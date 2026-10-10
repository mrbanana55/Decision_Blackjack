"""Validation of scenarios defined in quickstart.md."""

from app.engine.card import Card, Rank, Suit
from app.engine.round import BlackjackRound
from app.engine.rules import TableRules
from app.engine.shoe import Shoe
from app.engine.types import Action, RoundPhase


def test_quickstart_scenario_1_standard_round():
    """Scenario 1: Standard Round (Deal -> Hit -> Stand -> Dealer Play -> Settlement)."""
    # 1. Initialize rules, shoe, and round
    rules = TableRules(min_bet=10.0, max_bet=500.0)
    shoe = Shoe(num_decks=6, seed=0)
    initial_bankroll = 1000.0

    round_engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=initial_bankroll)

    # 2. Place initial bet ($50)
    state = round_engine.start_round(bet=50.0)
    assert state.phase == RoundPhase.PLAYER_TURNS
    assert round_engine.current_bankroll == 950.0  # Immediate deduction (Clarification Q3)

    # 3. Check legal actions and take a Hit
    legal_actions = round_engine.get_legal_actions()
    assert Action.HIT in legal_actions
    assert Action.STAND in legal_actions

    state = round_engine.submit_action(Action.HIT)

    # 4. Stand if not busted
    if state.player_hands[0].status == "ACTIVE":
        state = round_engine.submit_action(Action.STAND)

    # 5. Play dealer deterministically to completion
    state = round_engine.play_dealer_to_end()
    assert state.phase == RoundPhase.SETTLEMENT

    # 6. Settle round and inspect financial outcomes
    settlement = round_engine.settle()
    assert settlement.final_bankroll > 0.0
    assert state.phase == RoundPhase.ROUND_COMPLETE


def test_quickstart_scenario_2_fifo_split():
    """Scenario 2: Test Controller with Pre-Arranged Card Sequence (FIFO Injection)."""
    # Inject exact sequence: Player 8, Dealer 6, Player 8, Dealer 7
    test_cards = [
        Card(Suit.HEARTS, Rank.EIGHT),
        Card(Suit.CLUBS, Rank.SIX),
        Card(Suit.SPADES, Rank.EIGHT),
        Card(Suit.DIAMONDS, Rank.SEVEN),
        # Additional cards for subsequent draws
        Card(Suit.HEARTS, Rank.THREE),  # Dealt to Hand 1 after Split
        Card(Suit.SPADES, Rank.TEN),    # Hit on Hand 1
        Card(Suit.CLUBS, Rank.TEN),     # Dealt to Hand 2 after Hand 1 completes
    ]

    shoe = Shoe(card_sequence=test_cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=1000.0)

    # Start round -> Player receives pair of 8s
    engine.start_round(bet=50.0)

    # Verify Split is legal
    assert Action.SPLIT in engine.get_legal_actions()

    # Execute Split -> Second bet deducted ($50), Hand 1 receives card sequentially (Clarification Q2 & Q3)
    state = engine.submit_action(Action.SPLIT)
    assert len(state.player_hands) == 2
    assert engine.current_bankroll == 900.0
    assert len(state.player_hands[0].cards) == 2  # Hand 1 has 8 + 3 = 11
    assert len(state.player_hands[1].cards) == 1  # Hand 2 waiting for sequential deal

    # Play Hand 1 -> Hit -> reaches 21 -> Stand
    engine.submit_action(Action.HIT)
    if state.player_hands[0].status == "ACTIVE":
        engine.submit_action(Action.STAND)

    # Hand 2 now receives its card (8 + 10 = 18) and becomes active
    state = engine.state
    assert state.active_hand_index == 1
    assert len(state.player_hands[1].cards) == 2

    # Stand Hand 2 -> Dealer plays -> Settle
    engine.submit_action(Action.STAND)
    engine.play_dealer_to_end()
    settlement = engine.settle()
    assert settlement.final_bankroll > 0.0
    assert state.phase == RoundPhase.ROUND_COMPLETE
