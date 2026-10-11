"""Domain models, comparison schemas, and evaluation oracle for Decision Blackjack."""

from typing import (TYPE_CHECKING, Any)
from app.engine.card import Rank
from app.engine.rules import TableRules
from app.engine.types import Action
from app.models.schemas import (
    BetComparison,
    BetSpreadConfig,
    DecisionCategory,
    DecisionComparison,
)
from app.models.strategy_matrices import get_optimal_action

if TYPE_CHECKING:
    from app.simulation.types import DecisionContext


class DecisionComparator:
    """Evaluation oracle comparing any player's decision or bet against Basic Strategy."""

    def __init__(
        self,
        rules: TableRules | None = None,
        spread_config: BetSpreadConfig | None = None,
    ) -> None:
        self.rules: TableRules = rules if rules is not None else TableRules()
        self.spread_config: BetSpreadConfig = spread_config if spread_config is not None else BetSpreadConfig()

    def _determine_category(self, context: Any, optimal_action: Action) -> DecisionCategory:
        if optimal_action == Action.SURRENDER or Action.SURRENDER in context.legal_actions and optimal_action == Action.SURRENDER:
            return DecisionCategory.SURRENDER

        cards = context.player_cards
        if len(cards) == 2 and (cards[0].rank == cards[1].rank or cards[0].nominal_value == cards[1].nominal_value == 10):
            if optimal_action == Action.SPLIT:
                return DecisionCategory.PAIR_SPLIT

        if context.is_soft and context.player_total <= 21:
            return DecisionCategory.SOFT_TOTAL

        return DecisionCategory.HARD_TOTAL

    def evaluate_turn_decision(
        self,
        context: Any,
        actual_action: Action,
    ) -> DecisionComparison:
        """Compare an agent's chosen action against what Basic Strategy dictates in that position."""
        optimal_action, reasoning = get_optimal_action(
            player_cards=context.player_cards,
            player_total=context.player_total,
            is_soft=context.is_soft,
            dealer_upcard=context.dealer_upcard,
            legal_actions=context.legal_actions,
            rules=self.rules,
        )

        category = self._determine_category(context, optimal_action)
        is_legal = actual_action in context.legal_actions
        is_optimal = (actual_action == optimal_action)

        return DecisionComparison(
            is_optimal=is_optimal,
            optimal_action=optimal_action,
            actual_action=actual_action,
            category=category,
            reasoning=reasoning,
            is_legal=is_legal,
            metadata={"positional_eval": True},
        )

    def evaluate_round_bet(
        self,
        actual_bet: float,
        min_bet: float,
        true_count: float,
        bankroll: float,
    ) -> BetComparison:
        """Compare an agent's opening wager against what Basic Strategy dictates for that True Count."""
        if true_count <= 0.0:
            units = 1
        else:
            units = min(self.spread_config.max_spread_multiplier, max(1, int(true_count)))

        target_bet = float(units * min_bet)
        optimal_bet = min(bankroll, target_bet)

        is_bet_optimal = (actual_bet == optimal_bet)
        bet_delta = round(actual_bet - optimal_bet, 2)
        reasoning = (
            f"TC={true_count:.1f} warrants {units}x min_bet (${optimal_bet:.2f}). "
            f"Actual bet was ${actual_bet:.2f} (delta: ${bet_delta:+.2f})."
        )

        return BetComparison(
            is_bet_optimal=is_bet_optimal,
            optimal_bet=optimal_bet,
            actual_bet=actual_bet,
            bet_delta=bet_delta,
            true_count=true_count,
            reasoning=reasoning,
        )


__all__ = [
    "BetComparison",
    "BetSpreadConfig",
    "DecisionCategory",
    "DecisionComparison",
    "DecisionComparator",
]
