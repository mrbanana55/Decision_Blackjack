"""Autonomous DecisionProvider adapter for local Laya deep learning model inference."""

import logging
from typing import Any

import httpx

from app.engine.rules import TableRules
from app.engine.types import Action
from app.integrations.laya.builder import LayaSchemaBuilder
from app.integrations.laya.client import LayaClient
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


class LayaAgent:
    """Blackjack decision agent communicating with a local Laya inference server."""

    def __init__(
        self,
        name: str = "Laya",
        client: LayaClient | None = None,
        builder: LayaSchemaBuilder | None = None,
        rules: TableRules | None = None,
        default_bankroll: float = 1000.0,
    ) -> None:
        self._name = name
        self.client = client or LayaClient()
        self.builder = builder or LayaSchemaBuilder()
        self.rules = rules or TableRules()
        self.current_bankroll = default_bankroll

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_type(self) -> EntityType:
        return EntityType.LAYA

    def set_rules(self, rules: TableRules) -> None:
        """Update active table rules governing decisions."""
        self.rules = rules

    def update_bankroll(self, bankroll: float) -> None:
        """Update the agent's tracked bankroll balance."""
        self.current_bankroll = bankroll

    async def get_decision(self, context: DecisionContext) -> AgentDecision:
        """Query local Laya for an in-hand action decision."""
        request = self.builder.build_hand_decision_request(
            context=context,
            rules=self.rules,
            bankroll=self.current_bankroll,
        )

        response = await self.client.send_systemone(request)
        answer = response.answers.get("action")

        if answer is None or not answer.choice:
            raise AgentFaultError("Laya response missing valid 'action' choice answer")

        choice_key = answer.choice.lower().strip()
        action = CHOICE_TO_ACTION.get(choice_key)

        if action is None:
            # Fallback attempt: check if choice matches enum name directly
            try:
                action = Action[choice_key.upper()]
            except KeyError:
                raise AgentFaultError(f"Laya returned unrecognized action '{choice_key}'") from None

        if action not in context.legal_actions:
            logger.warning(
                "Laya chose action %s which is not in legal_actions %s; falling back to Stand/Hit",
                action,
                context.legal_actions,
            )
            # Default to stand if legal, else first legal action
            action = Action.STAND if Action.STAND in context.legal_actions else context.legal_actions[0]

        latency_ms = float(response.meta.get("latency_ms", 0.0))
        metadata: dict[str, Any] = {
            "provider": "laya",
            "endpoint": "/v1/systemone",
            "situation": self.builder.detect_hand_situation(context).value,
            "distribution": answer.distribution,
            **response.meta,
        }

        return AgentDecision(
            action=action,
            confidence=answer.confidence,
            latency_ms=latency_ms,
            reasoning=f"Laya local policy chose {action.name} (confidence {answer.confidence:.2f})",
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
        """Query Laya for opening round bet sizing."""
        self.current_bankroll = bankroll
        rules = TableRules(min_bet=min_bet)

        request = self.builder.build_betting_request(
            bankroll=bankroll,
            rules=rules,
            true_count=true_count,
            cards_seen=cards_seen,
            total_cards=total_cards,
            round_number=round_number,
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
            logger.warning("Laya get_bet query failed: %s; defaulting to minimum bet", exc)

        return min(min_bet, bankroll)

    async def get_insurance(
        self,
        context: DecisionContext,
        insurance_cost: float,
    ) -> bool:
        """Query Laya for insurance side bet decision when dealer shows an Ace."""
        request = self.builder.build_insurance_request(
            context=context,
            insurance_cost=insurance_cost,
            bankroll=self.current_bankroll,
        )

        try:
            response = await self.client.send_systemone(request)
            answer = response.answers.get("insurance")
            if answer and answer.choice:
                return answer.choice.lower().strip() == "accept"
        except (httpx.HTTPError, AgentFaultError, KeyError, ValueError, RuntimeError) as exc:
            logger.warning("Laya insurance query failed: %s; defaulting to decline", exc)

        return False
