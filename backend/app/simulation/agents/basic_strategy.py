"""Mathematical Blackjack Basic Strategy decision provider."""

from typing import Any
from app.engine.card import Card, Rank
from app.engine.types import Action
from app.simulation.interfaces import DecisionProvider
from app.simulation.types import AgentDecision, DecisionContext, EntityType


class BasicStrategyAgent:
    """Deterministic basic strategy decision provider adhering to optimal game theory."""

    def __init__(self, name: str = "OptimalStrategy") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_type(self) -> EntityType:
        return EntityType.OPTIMAL

    def _get_dealer_value(self, upcard: Card) -> int:
        return upcard.nominal_value

    def _determine_action(self, context: DecisionContext) -> tuple[Action, str]:
        cards = context.player_cards
        dealer_val = self._get_dealer_value(context.dealer_upcard)
        legal = set(context.legal_actions)

        # 1. Pair Splitting (2 cards of same rank/nominal value)
        if len(cards) == 2 and (cards[0].rank == cards[1].rank or cards[0].nominal_value == cards[1].nominal_value):
            rank = cards[0].rank
            # Always split Aces and 8s
            if rank in (Rank.ACE, Rank.EIGHT):
                if Action.SPLIT in legal:
                    return Action.SPLIT, f"Split pair of {rank.name}s"
            # 9,9: Split vs 2-6, 8-9; Stand vs 7, 10, A
            elif rank == Rank.NINE:
                if dealer_val in (2, 3, 4, 5, 6, 8, 9) and Action.SPLIT in legal:
                    return Action.SPLIT, "Split 9s vs dealer 2-6, 8-9"
                if dealer_val in (7, 10, 11) and Action.STAND in legal:
                    return Action.STAND, "Stand on 9,9 vs dealer 7, 10, A"
            # 7,7: Split vs 2-7
            elif rank == Rank.SEVEN:
                if dealer_val <= 7 and Action.SPLIT in legal:
                    return Action.SPLIT, "Split 7s vs dealer 2-7"
            # 6,6: Split vs 2-6
            elif rank == Rank.SIX:
                if dealer_val <= 6 and Action.SPLIT in legal:
                    return Action.SPLIT, "Split 6s vs dealer 2-6"
            # 3,3 and 2,2: Split vs 2-7
            elif rank in (Rank.THREE, Rank.TWO):
                if dealer_val <= 7 and Action.SPLIT in legal:
                    return Action.SPLIT, f"Split {rank.name}s vs dealer 2-7"
            # 4,4: Split vs 5-6 if double allowed
            elif rank == Rank.FOUR:
                if dealer_val in (5, 6) and Action.SPLIT in legal:
                    return Action.SPLIT, "Split 4s vs dealer 5-6"
            # 5,5: Never split; treat as hard 10 below

        # 2. Surrender
        if Action.SURRENDER in legal and len(cards) == 2 and not context.is_soft:
            if context.player_total == 16 and dealer_val in (9, 10, 11):
                return Action.SURRENDER, "Surrender 16 vs dealer 9, 10, A"
            if context.player_total == 15 and dealer_val == 10:
                return Action.SURRENDER, "Surrender 15 vs dealer 10"

        # 3. Soft Totals
        if context.is_soft and context.player_total <= 21:
            total = context.player_total
            if total >= 20:
                return Action.STAND, f"Stand on soft {total}"
            if total == 19:
                if dealer_val == 6 and Action.DOUBLE in legal:
                    return Action.DOUBLE, "Double soft 19 vs dealer 6"
                return Action.STAND, "Stand on soft 19"
            if total == 18:
                if dealer_val in (2, 3, 4, 5, 6) and Action.DOUBLE in legal:
                    return Action.DOUBLE, "Double soft 18 vs dealer 2-6"
                if dealer_val in (7, 8):
                    return Action.STAND, "Stand on soft 18 vs dealer 7-8"
                return Action.HIT, "Hit soft 18 vs dealer 9, 10, A"
            if total == 17:
                if dealer_val in (3, 4, 5, 6) and Action.DOUBLE in legal:
                    return Action.DOUBLE, "Double soft 17 vs dealer 3-6"
                return Action.HIT, "Hit soft 17"
            if total in (15, 16):
                if dealer_val in (4, 5, 6) and Action.DOUBLE in legal:
                    return Action.DOUBLE, f"Double soft {total} vs dealer 4-6"
                return Action.HIT, f"Hit soft {total}"
            if total in (13, 14):
                if dealer_val in (5, 6) and Action.DOUBLE in legal:
                    return Action.DOUBLE, f"Double soft {total} vs dealer 5-6"
                return Action.HIT, f"Hit soft {total}"

        # 4. Hard Totals
        total = context.player_total
        if total >= 17:
            return Action.STAND, f"Stand on hard {total}"
        if total in (13, 14, 15, 16):
            if dealer_val <= 6:
                return Action.STAND, f"Stand on hard {total} vs dealer {dealer_val}"
            return Action.HIT, f"Hit hard {total} vs dealer {dealer_val}"
        if total == 12:
            if dealer_val in (4, 5, 6):
                return Action.STAND, f"Stand on hard 12 vs dealer {dealer_val}"
            return Action.HIT, f"Hit hard 12 vs dealer {dealer_val}"
        if total == 11:
            if Action.DOUBLE in legal:
                return Action.DOUBLE, "Double hard 11"
            return Action.HIT, "Hit hard 11"
        if total == 10:
            if dealer_val <= 9 and Action.DOUBLE in legal:
                return Action.DOUBLE, "Double hard 10 vs dealer 2-9"
            return Action.HIT, "Hit hard 10"
        if total == 9:
            if dealer_val in (3, 4, 5, 6) and Action.DOUBLE in legal:
                return Action.DOUBLE, "Double hard 9 vs dealer 3-6"
            return Action.HIT, "Hit hard 9"

        # 8 or below
        return Action.HIT, f"Hit hard {total}"

    async def get_decision(self, context: DecisionContext) -> AgentDecision:
        """Produce an action decision using basic strategy."""
        action, reasoning = self._determine_action(context)

        # Safety: Ensure the chosen action is currently legal in this round state
        if action not in context.legal_actions:
            if action == Action.DOUBLE and Action.HIT in context.legal_actions:
                action = Action.HIT
                reasoning += " (Double not allowed, hit instead)"
            elif Action.STAND in context.legal_actions and (context.player_total >= 17 or context.is_soft):
                action = Action.STAND
            elif Action.HIT in context.legal_actions:
                action = Action.HIT
            elif context.legal_actions:
                action = context.legal_actions[0]

        return AgentDecision(
            action=action,
            confidence=1.0,
            latency_ms=0.05,
            reasoning=reasoning,
            metadata={"strategy": "basic_strategy", "optimal": True},
        )
