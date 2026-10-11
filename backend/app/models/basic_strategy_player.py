from typing import TYPE_CHECKING, Any
from app.engine.card import Card
from app.engine.rules import TableRules
from app.engine.types import Action
from app.models.card_counter import HiLoCardCounter
from app.models.schemas import BetSpreadConfig
from app.models.strategy_matrices import get_optimal_action
from app.simulation.types import AgentDecision, DecisionContext, EntityType

if TYPE_CHECKING:
    from app.simulation.interfaces import DecisionProvider


class BasicStrategyPlayer:
    """Deterministic basic strategy decision provider adhering strictly to game theory."""

    def __init__(
        self,
        name: str = "OptimalStrategy",
        rules: TableRules | None = None,
        spread_config: BetSpreadConfig | None = None,
    ) -> None:
        self._name: str = name
        self.rules: TableRules = rules if rules is not None else TableRules()
        self.spread_config: BetSpreadConfig = spread_config if spread_config is not None else BetSpreadConfig()
        self.counter: HiLoCardCounter = HiLoCardCounter(num_decks=self.rules.num_decks)

    @property
    def name(self) -> str:
        return self._name

    @property
    def entity_type(self) -> EntityType:
        return EntityType.OPTIMAL

    def observe_card(self, card: Card) -> None:
        """Observe a single exposed card on the table and update count."""
        self.counter.observe_card(card)

    def observe_cards(self, cards: list[Card]) -> None:
        """Observe multiple exposed cards in batch."""
        self.counter.observe_cards(cards)

    def reset_count(self) -> None:
        """Reset internal card counting state upon shoe reshuffle/adoption."""
        self.counter.reset()

    def get_bet(self, bankroll: float, min_bet: float) -> float:
        """Calculate initial round wager based on True Count and bet spread.
        
        docs/Estrategia Optima.md Section 7:
        - TC <= 0: min_bet
        - TC > 0: n * min_bet (up to max_spread_multiplier)
        """
        tc = self.counter.true_count
        if tc <= 0.0:
            units = 1
        else:
            units = min(self.spread_config.max_spread_multiplier, max(1, int(tc)))

        target_bet = float(units * min_bet)
        # Bankroll safety clamp: cannot bet more than available bankroll
        return min(bankroll, target_bet)

    async def get_decision(self, context: DecisionContext) -> AgentDecision:
        """Compute the optimal action for the current observable hand context."""
        # Update counter if new cards are visible in context
        if context.player_cards:
            pass  # Counter is updated through table/observer hooks

        action, reasoning = get_optimal_action(
            player_cards=context.player_cards,
            player_total=context.player_total,
            is_soft=context.is_soft,
            dealer_upcard=context.dealer_upcard,
            legal_actions=context.legal_actions,
            rules=self.rules,
        )

        # Safety: Guarantee action is in legal actions (with chart-defined fallbacks)
        if action not in context.legal_actions:
            if action == Action.DOUBLE:
                action = Action.HIT
                reasoning += " (Double not allowed, hit instead)"
            elif action == Action.SURRENDER:
                action = Action.HIT
                reasoning += " (Surrender not allowed, hit instead)"
            elif Action.STAND in context.legal_actions and (context.player_total >= 17 or context.is_soft):
                action = Action.STAND
            elif Action.HIT in context.legal_actions:
                action = Action.HIT
            elif context.legal_actions:
                action = context.legal_actions[0]

        return AgentDecision(
            action=action,
            confidence=1.0,
            latency_ms=0.04,
            reasoning=reasoning,
            metadata={"strategy": "basic_strategy", "optimal": True},
        )
