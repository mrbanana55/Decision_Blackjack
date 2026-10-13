"""Autonomous DecisionProvider adapter for TypeSafe Jev System One model inference."""

import logging
from typing import Any

import httpx

from app.engine.rules import TableRules
from app.engine.types import Action
from app.integrations.jev.builder import JevSchemaBuilder
from app.integrations.jev.client import JevClient
from app.integrations.jev.config import JevConfig
from app.simulation.interfaces import AgentFaultError
from app.simulation.types import AgentDecision, DecisionContext, EntityType

logger = logging.getLogger(__name__)

CHOICE_TO_ACTION: dict[str, Action] = {
    "hit": Action.HIT,
    "stand": Action.STAND,
    "double": Action.DOUBLE,
    "split": Action.SPLIT,
    "surrender": Action.SURRENDER,
}


class JevAgent:
    """Blackjack decision agent communicating with TypeSafe Jev System One API."""

    def __init__(
        self,
        name: str = "Jev",
        client: JevClient | None = None,
        builder: JevSchemaBuilder | None = None,
        rules: TableRules | None = None,
        default_bankroll: float = 1000.0,
        config: JevConfig | None = None,
    ) -> None:
        self._name = name
        if config:
            self.config = config
        elif client and hasattr(client, "config") and isinstance(client.config, JevConfig):
            self.config = client.config
        else:
            self.config = JevConfig()
        self.client = client or JevClient(config=self.config)
        self.builder = builder or JevSchemaBuilder()
        self.rules = rules or TableRules()
        self.current_bankroll = default_bankroll

    @property
    def model_name(self) -> str:
        model_val = getattr(self.config, "model", "jev-latest")
        if isinstance(model_val, str):
            return model_val
        return "jev-latest"

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_type(self) -> EntityType:
        return EntityType.JEV

    def set_rules(self, rules: TableRules) -> None:
        """Update active table rules governing decisions."""
        self.rules = rules

    def update_bankroll(self, bankroll: float) -> None:
        """Update the agent's tracked bankroll balance."""
        self.current_bankroll = bankroll

    async def get_decision(self, context: DecisionContext) -> AgentDecision:
        """Query TypeSafe Jev for an in-hand action decision."""
        request = self.builder.build_hand_decision_request(
            context=context,
            rules=self.rules,
            bankroll=self.current_bankroll,
            model=self.model_name,
        )

        response = await self.client.send_systemone(request)
        answer = response.answers.get("action")

        if answer is None or not answer.choice:
            raise AgentFaultError("Jev response missing valid 'action' choice answer")

        choice_key = answer.choice.lower().strip()
        action = CHOICE_TO_ACTION.get(choice_key)

        if action is None:
            try:
                action = Action[choice_key.upper()]
            except KeyError:
                raise AgentFaultError(f"Jev returned unrecognized action '{choice_key}'") from None

        if action not in context.legal_actions:
            logger.warning(
                "Jev chose action %s which is not in legal_actions %s; falling back to Stand/Hit",
                action,
                context.legal_actions,
            )
            action = (
                Action.STAND
                if Action.STAND in context.legal_actions
                else context.legal_actions[0]
            )

        latency_ms = float(response.meta.get("latency_ms", 0.0))
        metadata: dict[str, Any] = {
            "provider": "typesafe",
            "model": response.model,
            "endpoint": self.config.get_effective_url(),
            "situation": self.builder.detect_hand_situation(context).value,
            "probabilities": answer.probabilities,
            "distribution": answer.probabilities,
            "input_tokens": response.usage.input_tokens if response.usage else None,
            "output_tokens": response.usage.output_tokens if response.usage else None,
            "request_payload": request.model_dump(),
            "response_payload": response.model_dump(),
            **response.meta,
        }

        return AgentDecision(
            action=action,
            confidence=answer.confidence,
            latency_ms=latency_ms,
            reasoning=f"Jev System One chose {action.name} (confidence {answer.confidence:.2f})",
            metadata=metadata,
        )

    async def get_bet(
        self,
        bankroll: float,
        min_bet: float,
        true_count: float = 0.0,
        cards_seen: int = 0,
        total_cards: int = 312,
        round_number: int = 1,
    ) -> float:
        """Query Jev for opening round bet sizing."""
        self.current_bankroll = bankroll
        rules = TableRules(min_bet=min_bet)

        request = self.builder.build_betting_request(
            bankroll=bankroll,
            rules=rules,
            true_count=true_count,
            cards_seen=cards_seen,
            total_cards=total_cards,
            round_number=round_number,
            model=self.model_name,
        )

        try:
            response = await self.client.send_systemone(request)
            answer = response.answers.get("bet_sizing")
            if answer and answer.choice:
                choice = answer.choice.lower().strip()
                multiplier_map = {
                    "1x": 1.0,
                    "2x": 2.0,
                    "4x": 4.0,
                    "8x": 8.0,
                    "min": 1.0,
                }
                mult = multiplier_map.get(choice, 1.0)
                calculated_bet = min_bet * mult
                return min(calculated_bet, bankroll)
        except (httpx.HTTPError, AgentFaultError, KeyError, ValueError, RuntimeError) as exc:
            logger.warning("Jev get_bet query failed: %s; defaulting to minimum bet", exc)

        return min(min_bet, bankroll)

    async def get_insurance(
        self,
        context: DecisionContext,
        insurance_cost: float,
    ) -> bool:
        """Query Jev for insurance side bet decision when dealer shows an Ace."""
        request = self.builder.build_insurance_request(
            context=context,
            insurance_cost=insurance_cost,
            bankroll=self.current_bankroll,
            model=self.model_name,
        )

        try:
            response = await self.client.send_systemone(request)
            answer = response.answers.get("insurance")
            if answer and answer.choice:
                return answer.choice.lower().strip() == "accept"
        except (httpx.HTTPError, AgentFaultError, KeyError, ValueError, RuntimeError) as exc:
            logger.warning("Jev insurance query failed: %s; defaulting to decline", exc)

        return False
