"""Unit tests for standalone contextual DecisionComparator oracle."""

from app.engine.card import Card, Rank, Suit
from app.engine.rules import TableRules
from app.engine.types import Action
from app.models.decision_comparator import DecisionComparator, DecisionCategory
from app.simulation.types import DecisionContext


def _card(rank: Rank) -> Card:
    return Card(suit=Suit.SPADES, rank=rank)


def _make_context(
    player_cards: list[Card],
    dealer_upcard: Card,
    legal_actions: list[Action],
    player_total: int,
    is_soft: bool,
    true_count: float = 0.0,
) -> DecisionContext:
    return DecisionContext(
        session_id="test-sim",
        round_number=1,
        hand_index=0,
        player_cards=player_cards,
        player_total=player_total,
        is_soft=is_soft,
        dealer_upcard=dealer_upcard,
        legal_actions=legal_actions,
        true_count=true_count,
    )


def test_positional_turn_comparison_optimal_decision():
    """Verify comparator identifies when an agent decision is optimal."""
    comparator = DecisionComparator()

    # Jev has hard 15 vs dealer 2, and stands (optimal action)
    ctx = _make_context(
        player_cards=[_card(Rank.TEN), _card(Rank.FIVE)],
        dealer_upcard=_card(Rank.TWO),
        legal_actions=[Action.HIT, Action.STAND],
        player_total=15,
        is_soft=False,
    )

    comp = comparator.evaluate_turn_decision(ctx, actual_action=Action.STAND)
    assert comp.is_optimal is True
    assert comp.optimal_action == Action.STAND
    assert comp.actual_action == Action.STAND
    assert comp.category == DecisionCategory.HARD_TOTAL
    assert "Stand on hard 15 vs dealer 2" in comp.reasoning


def test_positional_turn_comparison_suboptimal_decision():
    """Verify comparator identifies when an agent decision deviates from basic strategy."""
    comparator = DecisionComparator()

    # Laya has hard 12 vs dealer 5, and hits (suboptimal: chart says Stand)
    ctx = _make_context(
        player_cards=[_card(Rank.EIGHT), _card(Rank.FOUR)],
        dealer_upcard=_card(Rank.FIVE),
        legal_actions=[Action.HIT, Action.STAND],
        player_total=12,
        is_soft=False,
    )

    comp = comparator.evaluate_turn_decision(ctx, actual_action=Action.HIT)
    assert comp.is_optimal is False
    assert comp.optimal_action == Action.STAND
    assert comp.actual_action == Action.HIT
    assert comp.category == DecisionCategory.HARD_TOTAL


def test_positional_turn_comparison_pair_split_and_surrender():
    """Verify comparator classifies PAIR_SPLIT and SURRENDER categories."""
    rules = TableRules(double_after_split=True, surrender_rule="late")
    comparator = DecisionComparator(rules=rules)

    # Agent splits 8,8 vs 7 (optimal)
    ctx_split = _make_context(
        player_cards=[_card(Rank.EIGHT), _card(Rank.EIGHT)],
        dealer_upcard=_card(Rank.SEVEN),
        legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
        player_total=16,
        is_soft=False,
    )
    comp_split = comparator.evaluate_turn_decision(ctx_split, actual_action=Action.SPLIT)
    assert comp_split.is_optimal is True
    assert comp_split.category == DecisionCategory.PAIR_SPLIT

    # Agent hits 16 vs 10 when surrender is legal (suboptimal)
    ctx_surr = _make_context(
        player_cards=[_card(Rank.TEN), _card(Rank.SIX)],
        dealer_upcard=_card(Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND, Action.SURRENDER],
        player_total=16,
        is_soft=False,
    )
    comp_surr = comparator.evaluate_turn_decision(ctx_surr, actual_action=Action.HIT)
    assert comp_surr.is_optimal is False
    assert comp_surr.optimal_action == Action.SURRENDER
    assert comp_surr.category == DecisionCategory.SURRENDER


def test_round_bet_comparison():
    """Verify bet sizing evaluation against True Count bet spread."""
    comparator = DecisionComparator()

    # Case 1: TC = +2.0, min_bet = $50 -> Optimal bet = $100
    # Agent wagers $50 (underbetting)
    bet_comp1 = comparator.evaluate_round_bet(
        actual_bet=50.0,
        min_bet=50.0,
        true_count=2.0,
        bankroll=1000.0,
    )
    assert bet_comp1.is_bet_optimal is False
    assert bet_comp1.optimal_bet == 100.0
    assert bet_comp1.actual_bet == 50.0
    assert bet_comp1.bet_delta == -50.0

    # Case 2: TC = -1.0, min_bet = $50 -> Optimal bet = $50
    # Agent wagers $50 (optimal)
    bet_comp2 = comparator.evaluate_round_bet(
        actual_bet=50.0,
        min_bet=50.0,
        true_count=-1.0,
        bankroll=1000.0,
    )
    assert bet_comp2.is_bet_optimal is True
    assert bet_comp2.optimal_bet == 50.0
    assert bet_comp2.bet_delta == 0.0


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All decision comparator tests passed!")
