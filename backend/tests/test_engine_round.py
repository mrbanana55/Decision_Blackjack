"""Lifecycle playthrough unit tests for the core Blackjack round finite state machine."""

from app.engine.card import Card, Rank, Suit
from app.engine.interfaces import InsufficientFundsError, InvalidBetError, InvalidStateError
from app.engine.round import BlackjackRound, RoundState
from app.engine.rules import TableRules
from app.engine.shoe import Shoe
from app.engine.types import Action, HandStatus, RoundPhase, SettlementOutcome


def test_initial_deal_and_immediate_bankroll_deduction():
    """Verify bankroll deduction occurs immediately upon placing bet."""
    rules = TableRules(min_bet=10.0, max_bet=500.0)
    cards = [
        Card(Suit.CLUBS, Rank.SEVEN),     # Player 1
        Card(Suit.HEARTS, Rank.TEN),      # Dealer 1 (upcard)
        Card(Suit.SPADES, Rank.FIVE),     # Player 2
        Card(Suit.DIAMONDS, Rank.EIGHT),   # Dealer 2 (hole card)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

    assert engine.phase == RoundPhase.AWAITING_BET
    assert engine.current_bankroll == 1000.0

    state = engine.start_round(bet=50.0)

    assert engine.current_bankroll == 950.0
    assert state.player_bankroll == 950.0
    assert state.phase == RoundPhase.PLAYER_TURNS
    assert len(state.player_hands) == 1
    assert len(state.player_hands[0].cards) == 2
    assert state.player_hands[0].total == 12
    assert state.dealer_hand.visible_total == 10
    assert not state.dealer_hand.is_revealed


def test_hit_stand_dealer_play_and_settlement():
    """Verify player hit, stand, dealer drawing to 17+, and settlement win."""
    rules = TableRules(min_bet=10.0, max_bet=500.0)
    cards = [
        Card(Suit.CLUBS, Rank.SEVEN),     # Player 1 (7)
        Card(Suit.HEARTS, Rank.TEN),      # Dealer 1 (10)
        Card(Suit.SPADES, Rank.FIVE),     # Player 2 (5 -> total 12)
        Card(Suit.DIAMONDS, Rank.EIGHT),   # Dealer 2 (8 -> total 18)
        Card(Suit.CLUBS, Rank.NINE),      # Player Hit (9 -> total 21)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=50.0)
    legal = engine.get_legal_actions()
    assert Action.HIT in legal
    assert Action.STAND in legal

    state = engine.submit_action(Action.HIT)
    assert state.player_hands[0].total == 21

    # Stand if active
    if state.player_hands[0].status == HandStatus.ACTIVE:
        state = engine.submit_action(Action.STAND)

    assert state.player_hands[0].status in (HandStatus.STOOD, HandStatus.ACTIVE)
    assert engine.phase in (RoundPhase.DEALER_TURN, RoundPhase.SETTLEMENT)

    # Execute dealer turn
    state = engine.play_dealer_to_end()
    assert state.phase == RoundPhase.SETTLEMENT
    assert engine.dealer_hand.is_revealed
    assert engine.dealer_hand.total == 18

    # Settlement
    settlement = engine.settle()
    assert engine.phase == RoundPhase.ROUND_COMPLETE
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.WIN
    assert settlement.hand_outcomes[0].net_profit == 50.0
    assert settlement.gross_return == 100.0
    assert settlement.final_bankroll == 1050.0
    assert engine.current_bankroll == 1050.0


def test_player_bust_forfeits_bet_without_dealer_draw():
    """Verify player bust immediately terminates hand and dealer does not need to draw."""
    cards = [
        Card(Suit.CLUBS, Rank.TEN),       # Player 1 (10)
        Card(Suit.HEARTS, Rank.SEVEN),    # Dealer 1 (7)
        Card(Suit.SPADES, Rank.SIX),      # Player 2 (6 -> total 16)
        Card(Suit.DIAMONDS, Rank.SEVEN),  # Dealer 2 (7 -> total 14)
        Card(Suit.CLUBS, Rank.TEN),       # Player Hit (10 -> total 26 BUST)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=500.0)

    engine.start_round(bet=50.0)
    assert engine.current_bankroll == 450.0

    state = engine.submit_action(Action.HIT)
    assert state.player_hands[0].is_busted
    assert state.player_hands[0].status == HandStatus.BUSTED

    # Since all player hands busted, phase transitions to SETTLEMENT
    assert state.phase == RoundPhase.SETTLEMENT

    settlement = engine.settle()
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.LOSS
    assert settlement.hand_outcomes[0].net_profit == -50.0
    assert settlement.gross_return == 0.0
    assert settlement.final_bankroll == 450.0
    assert engine.current_bankroll == 450.0


def test_dealer_hits_and_busts():
    """Verify dealer hits below 17 and busts when drawing over 21."""
    cards = [
        Card(Suit.CLUBS, Rank.TEN),       # Player 1 (10)
        Card(Suit.HEARTS, Rank.SIX),      # Dealer 1 (6)
        Card(Suit.SPADES, Rank.NINE),     # Player 2 (9 -> total 19)
        Card(Suit.DIAMONDS, Rank.SEVEN),  # Dealer 2 (7 -> dealer total 13)
        Card(Suit.CLUBS, Rank.KING),      # Dealer draw (10 -> dealer total 23 BUST)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=100.0)
    engine.submit_action(Action.STAND)

    state = engine.play_dealer_to_end()
    assert state.dealer_hand.is_busted
    assert state.dealer_hand.total == 23

    settlement = engine.settle()
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.WIN
    assert settlement.hand_outcomes[0].net_profit == 100.0
    assert settlement.final_bankroll == 1100.0


def test_natural_blackjack_direct_payout():
    """Verify Natural Blackjack with upcard < 10 pays 3:2 immediately."""
    cards = [
        Card(Suit.CLUBS, Rank.ACE),       # Player 1
        Card(Suit.HEARTS, Rank.SIX),      # Dealer 1 (6)
        Card(Suit.SPADES, Rank.KING),     # Player 2 -> Natural BJ!
        Card(Suit.DIAMONDS, Rank.EIGHT),  # Dealer 2 (8)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=1000.0)

    state = engine.start_round(bet=100.0)
    # Dealer upcard is 6, cannot have BJ -> round transitions to SETTLEMENT
    assert state.phase == RoundPhase.SETTLEMENT
    assert state.player_hands[0].is_blackjack

    settlement = engine.settle()
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.NATURAL_BLACKJACK
    assert settlement.hand_outcomes[0].net_profit == 150.0  # 3:2 on 100
    assert settlement.gross_return == 250.0
    assert settlement.final_bankroll == 1150.0


def test_push_returns_stake():
    """Verify push refunds exact bet without net profit."""
    cards = [
        Card(Suit.CLUBS, Rank.TEN),       # Player 1
        Card(Suit.HEARTS, Rank.TEN),      # Dealer 1
        Card(Suit.SPADES, Rank.EIGHT),    # Player 2 -> 18
        Card(Suit.DIAMONDS, Rank.EIGHT),  # Dealer 2 -> 18
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=500.0)

    engine.start_round(bet=50.0)
    engine.submit_action(Action.STAND)
    engine.play_dealer_to_end()
    settlement = engine.settle()

    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.PUSH
    assert settlement.hand_outcomes[0].net_profit == 0.0
    assert settlement.gross_return == 50.0
    assert settlement.final_bankroll == 500.0


def test_invalid_bet_and_insufficient_funds_rejection():
    """Verify boundary bet errors and insufficient funds."""
    rules = TableRules(min_bet=10.0, max_bet=100.0)
    engine = BlackjackRound(rules=rules, shoe=Shoe(), player_bankroll=50.0)

    # Below min bet
    try:
        engine.start_round(bet=5.0)
        assert False, "Should have raised InvalidBetError"
    except InvalidBetError:
        pass

    # Above max bet
    try:
        engine.start_round(bet=150.0)
        assert False, "Should have raised InvalidBetError"
    except InvalidBetError:
        pass

    # Exceeds bankroll
    try:
        engine.start_round(bet=60.0)
        assert False, "Should have raised InsufficientFundsError"
    except InsufficientFundsError:
        pass

    # State and bankroll unchanged
    assert engine.phase == RoundPhase.AWAITING_BET
    assert engine.current_bankroll == 50.0
