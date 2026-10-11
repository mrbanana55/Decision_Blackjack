"""Isolated entity table managing a single DecisionProvider, BlackjackRound, and metrics."""

from app.engine.round import BlackjackRound, RoundState
from app.engine.rules import TableRules
from app.engine.settlement import RoundSettlement
from app.engine.shoe import Shoe
from app.engine.types import Action, RoundPhase, SettlementOutcome
from app.models.decision_comparator import DecisionComparator, DecisionComparison
from app.simulation.interfaces import DecisionProvider, IllegalAgentActionError
from app.simulation.types import (
    AgentDecision,
    DecisionContext,
    EntityType,
    SimulationMetrics,
)


class EntityTable:
    """Manages an isolated Blackjack table for a specific decision entity."""

    def __init__(
        self,
        entity_id: str,
        provider: DecisionProvider,
        rules: TableRules | None = None,
        shoe: Shoe | None = None,
        initial_bankroll: float = 1000.0,
        shoe_generation: int = 0,
    ) -> None:
        self.entity_id: str = entity_id
        self.provider: DecisionProvider = provider
        self.rules: TableRules = rules if rules is not None else TableRules()
        self.starting_bankroll: float = float(initial_bankroll)
        self.shoe_generation: int = shoe_generation
        self.is_eliminated: bool = False
        self.comparator: DecisionComparator = DecisionComparator(rules=self.rules)

        active_shoe = shoe if shoe is not None else Shoe(num_decks=self.rules.num_decks)
        self.round_engine: BlackjackRound = BlackjackRound(
            rules=self.rules,
            shoe=active_shoe,
            player_bankroll=self.starting_bankroll,
        )

        self.rounds_played: int = 0
        self.wins: int = 0
        self.losses: int = 0
        self.pushes: int = 0
        self.blackjacks: int = 0
        self.optimal_decisions: int = 0
        self.suboptimal_decisions: int = 0
        self.last_decision: AgentDecision | None = None
        self.last_comparison: DecisionComparison | None = None

    @property
    def entity_type(self) -> EntityType:
        return self.provider.entity_type

    @property
    def current_bankroll(self) -> float:
        return self.round_engine.current_bankroll

    @property
    def phase(self) -> RoundPhase:
        return self.round_engine.phase

    @property
    def state(self) -> RoundState:
        return self.round_engine.state

    @property
    def reshuffle_needed(self) -> bool:
        return self.round_engine.shoe.reshuffle_needed

    @property
    def metrics(self) -> SimulationMetrics:
        """Construct cumulative performance metrics for this entity."""
        return SimulationMetrics(
            entity_id=self.entity_id,
            entity_type=self.entity_type,
            rounds_played=self.rounds_played,
            starting_bankroll=self.starting_bankroll,
            current_bankroll=self.current_bankroll,
            net_profit=round(self.current_bankroll - self.starting_bankroll, 2),
            wins=self.wins,
            losses=self.losses,
            pushes=self.pushes,
            blackjacks=self.blackjacks,
            is_eliminated=self.is_eliminated,
            optimal_decisions=self.optimal_decisions,
            suboptimal_decisions=self.suboptimal_decisions,
        )

    def adopt_shoe(self, shoe: Shoe, generation: int) -> None:
        """Replace active shoe with a new generation from the shoe pool."""
        self.round_engine.shoe = shoe
        self.shoe_generation = generation
        if hasattr(self.provider, "reset_count"):
            self.provider.reset_count()

    def start_round(self, bet: float | None = None) -> RoundState:
        """Initiate round with table bet if entity has sufficient funds."""
        if self.is_eliminated:
            raise RuntimeError(f"Entity '{self.entity_id}' is bankrupt and eliminated.")

        if self.reshuffle_needed and hasattr(self.provider, "reset_count"):
            self.provider.reset_count()

        # Query provider.get_bet() if bet is not explicitly supplied (FR-008)
        if bet is None:
            if hasattr(self.provider, "get_bet"):
                bet = self.provider.get_bet(
                    bankroll=self.current_bankroll,
                    min_bet=self.rules.min_bet,
                )
            else:
                bet = self.rules.min_bet

        state = self.round_engine.start_round(bet)

        # Notify provider of dealt player cards if it supports card observation
        if hasattr(self.provider, "observe_cards"):
            visible_cards = list(self.round_engine.player_hands[0].cards)
            if self.round_engine.dealer_hand.upcard:
                visible_cards.append(self.round_engine.dealer_hand.upcard)
            self.provider.observe_cards(visible_cards)

        return state

    async def play_turn(self, session_id: str = "", round_number: int = 1) -> AgentDecision | None:
        """Execute a single phase advancement or decision turn on this table."""
        if self.is_eliminated:
            return None

        # Insurance decision handling
        if self.round_engine.phase == RoundPhase.INSURANCE_OFFERED:
            # Basic / standard agents decline insurance
            self.round_engine.submit_insurance(accept=False)
            return None

        # Player turn decision handling
        if self.round_engine.phase == RoundPhase.PLAYER_TURNS:
            active_index = self.round_engine.active_hand_index
            if active_index >= len(self.round_engine.player_hands):
                return None

            hand = self.round_engine.player_hands[active_index]
            dealer_upcard = self.round_engine.dealer_hand.upcard
            legal_actions = self.round_engine.get_legal_actions()

            context = DecisionContext(
                session_id=session_id,
                round_number=round_number,
                hand_index=active_index,
                player_cards=list(hand.cards),
                player_total=hand.total,
                is_soft=hand.is_soft,
                dealer_upcard=dealer_upcard,
                legal_actions=list(legal_actions),
                can_insure=False,
                true_count=0.0,
            )

            decision = await self.provider.get_decision(context)

            # Validate legal action (FR-010)
            if decision.action not in legal_actions:
                raise IllegalAgentActionError(
                    f"Agent '{self.entity_id}' produced illegal action '{decision.action.value}'. "
                    f"Legal actions: {[a.value for a in legal_actions]}."
                )

            # Positional Decision Comparison Oracle Evaluation (FR-009)
            comparison = self.comparator.evaluate_turn_decision(context, decision.action)
            self.last_comparison = comparison
            if comparison.is_optimal:
                self.optimal_decisions += 1
            else:
                self.suboptimal_decisions += 1

            # Embed comparison in decision metadata for telemetry streaming
            decision.metadata["comparison"] = {
                "is_optimal": comparison.is_optimal,
                "optimal_action": comparison.optimal_action.value,
                "category": comparison.category.value,
                "reasoning": comparison.reasoning,
            }

            self.round_engine.submit_action(decision.action)
            self.last_decision = decision
            return decision

        # Dealer turn resolution
        if self.round_engine.phase == RoundPhase.DEALER_TURN:
            self.round_engine.play_dealer_to_end()
            return None

        # Settlement resolution
        if self.round_engine.phase == RoundPhase.SETTLEMENT:
            self.settle_round()
            return None

        return None

    def settle_round(self) -> RoundSettlement:
        """Finalize concluded round outcomes, payouts, and bankruptcy tracking."""
        settlement = self.round_engine.settle()
        self.rounds_played += 1

        for ho in settlement.hand_outcomes:
            if ho.outcome == SettlementOutcome.NATURAL_BLACKJACK:
                self.blackjacks += 1
                self.wins += 1
            elif ho.outcome == SettlementOutcome.WIN:
                self.wins += 1
            elif ho.outcome == SettlementOutcome.PUSH:
                self.pushes += 1
            elif ho.outcome in (SettlementOutcome.LOSS, SettlementOutcome.SURRENDER):
                self.losses += 1

        # Bankruptcy check (FR-012)
        if self.current_bankroll < self.rules.min_bet:
            self.is_eliminated = True

        return settlement

    async def step_round_to_completion(self, bet: float, session_id: str = "", round_number: int = 1) -> RoundSettlement:
        """Run an entire round from start to settlement sequentially on this table."""
        self.start_round(bet)

        while self.round_engine.phase not in (RoundPhase.ROUND_COMPLETE, RoundPhase.AWAITING_BET):
            if self.round_engine.phase == RoundPhase.INSURANCE_OFFERED:
                self.round_engine.submit_insurance(accept=False)
            elif self.round_engine.phase == RoundPhase.PLAYER_TURNS:
                await self.play_turn(session_id=session_id, round_number=round_number)
            elif self.round_engine.phase == RoundPhase.DEALER_TURN:
                self.round_engine.play_dealer_to_end()
            elif self.round_engine.phase == RoundPhase.SETTLEMENT:
                return self.settle_round()

        return self.round_engine.settlement or self.settle_round()
