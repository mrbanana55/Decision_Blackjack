"""End-to-end verification of scenarios from specs/003-basic-strategy-player/quickstart.md."""

import asyncio
from app.engine.card import Card, Rank, Suit
from app.engine.rules import TableRules
from app.engine.types import Action
from app.models.basic_strategy_player import BasicStrategyPlayer
from app.models.decision_comparator import DecisionComparator, DecisionCategory
from app.models.strategy_matrices import get_optimal_action
from app.simulation.types import DecisionContext


def _card(rank: Rank) -> Card:
    return Card(suit=Suit.SPADES, rank=rank)


def test_quickstart_scenario_1_matrix_adherence():
    """Scenario 1: Verify 100% Matrix Adherence Against docs/Estrategia Optima.md."""
    # 11 vs 10 -> DOUBLE (if allowed)
    action, reason = get_optimal_action(
        player_cards=[_card(Rank.SIX), _card(Rank.FIVE)],
        player_total=11,
        is_soft=False,
        dealer_upcard=_card(Rank.TEN),
        legal_actions=[Action.HIT, Action.STAND, Action.DOUBLE],
        rules=TableRules(),
    )
    assert action == Action.DOUBLE
    assert "Double hard 11" in reason


def test_quickstart_scenario_2_positional_decision_comparison():
    """Scenario 2: Positional Decision Comparison for External Agent (Jev/Laya).
    
    Demonstrate that when Jev plays 15 vs 2 and chooses Hit, the comparator detects
    the error (Basic Strategy stands on 15 vs 2).
    """
    comparator = DecisionComparator()
    ctx_15_vs_2 = DecisionContext(
        session_id="sim-quickstart",
        round_number=1,
        hand_index=0,
        player_cards=[_card(Rank.TEN), _card(Rank.FIVE)],
        player_total=15,
        is_soft=False,
        dealer_upcard=_card(Rank.TWO),
        legal_actions=[Action.HIT, Action.STAND],
        true_count=0.0,
    )

    # Jev mistakenly hits on hard 15 vs 2
    comparison = comparator.evaluate_turn_decision(
        context=ctx_15_vs_2,
        actual_action=Action.HIT,
    )
    assert comparison.is_optimal is False
    assert comparison.optimal_action == Action.STAND
    assert comparison.actual_action == Action.HIT
    assert comparison.category == DecisionCategory.HARD_TOTAL
    assert "Stand on hard 15 vs dealer 2" in comparison.reasoning


def test_quickstart_scenario_3_true_count_bet_comparison():
    """Scenario 3: True Count Bet Sizing Comparison.
    
    Demonstrate that when True Count is +3 with a $50 minimum bet, the expected bet is $150.
    If an agent wagers $50, the comparator records the delta.
    """
    comparator = DecisionComparator()
    bet_comp = comparator.evaluate_round_bet(
        actual_bet=50.0,
        min_bet=50.0,
        true_count=3.0,
        bankroll=1000.0,
    )
    assert bet_comp.is_bet_optimal is False
    assert bet_comp.optimal_bet == 150.0
    assert bet_comp.actual_bet == 50.0
    assert bet_comp.bet_delta == -100.0


def test_quickstart_scenario_4_autonomous_player_full_round():
    """Scenario 4: Fully functional Basic Strategy advantage player in orchestrator table."""
    player = BasicStrategyPlayer()
    # Feed cards to establish TC = +2.0
    player.observe_cards([_card(Rank.FOUR) for _ in range(12)])
    assert player.counter.true_count >= 2.0

    bet = player.get_bet(bankroll=1000.0, min_bet=50.0)
    assert bet >= 100.0

    async def _turn():
        ctx = DecisionContext(
            session_id="sim-quickstart",
            round_number=1,
            hand_index=0,
            player_cards=[_card(Rank.EIGHT), _card(Rank.EIGHT)],
            dealer_upcard=_card(Rank.SIX),
            legal_actions=[Action.HIT, Action.STAND, Action.SPLIT],
            player_total=16,
            is_soft=False,
        )
        dec = await player.get_decision(ctx)
        assert dec.action == Action.SPLIT

    asyncio.run(_turn())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All quickstart validation scenarios passed!")
