"""Unit tests for Split hands, Double Down, Insurance, and Surrender mechanics."""

from app.engine.card import Card, Rank, Suit
from app.engine.interfaces import IllegalActionError
from app.engine.round import BlackjackRound
from app.engine.rules import TableRules
from app.engine.shoe import Shoe
from app.engine.types import (
    Action,
    DealerStyle,
    HandStatus,
    RoundPhase,
    SettlementOutcome,
)


def test_sequential_split_playthrough():
    """Verify sequential dealing: Hand 1 plays to completion, then Hand 2 deals and plays."""
    test_cards = [
        Card(Suit.HEARTS, Rank.EIGHT),     # Player 1 (8)
        Card(Suit.CLUBS, Rank.SEVEN),      # Dealer 1 (7)
        Card(Suit.SPADES, Rank.EIGHT),     # Player 2 (8)
        Card(Suit.DIAMONDS, Rank.SEVEN),   # Dealer 2 (7)
        # Sequential draw cards:
        Card(Suit.HEARTS, Rank.THREE),     # Hand 1 2nd card (8 + 3 = 11)
        Card(Suit.SPADES, Rank.TEN),       # Hand 1 Hit (11 + 10 = 21)
        Card(Suit.CLUBS, Rank.TEN),        # Hand 2 2nd card (8 + 10 = 18)
    ]
    shoe = Shoe(card_sequence=test_cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=50.0)
    assert engine.current_bankroll == 950.0
    assert Action.SPLIT in engine.get_legal_actions()

    # Split Hand
    state = engine.submit_action(Action.SPLIT)
    assert len(state.player_hands) == 2
    assert engine.current_bankroll == 900.0  # Immediate deduction of second $50 bet
    assert len(state.player_hands[0].cards) == 2  # Hand 1 has 8 + 3 = 11
    assert len(state.player_hands[1].cards) == 1  # Hand 2 waiting for sequential deal

    # Play Hand 1: Hit (gets 10 -> 21)
    engine.submit_action(Action.HIT)
    assert state.player_hands[0].total == 21

    # Hand 1 is at 21, auto-stood, advancing to Hand 2!
    # Hand 2 automatically receives its sequential card (10) -> total 18
    assert engine.active_hand_index == 1
    assert len(state.player_hands[1].cards) == 2
    assert state.player_hands[1].total == 18

    # Stand Hand 2
    engine.submit_action(Action.STAND)
    assert engine.phase == RoundPhase.DEALER_TURN

    # Dealer plays: 7 + 7 = 14 -> must hit (<17) -> Shoe depleted, draws from discard
    engine.play_dealer_to_end()
    settlement = engine.settle()

    assert len(settlement.hand_outcomes) == 2
    assert settlement.hand_outcomes[0].player_total == 21
    assert settlement.hand_outcomes[1].player_total == 18


def test_split_aces_auto_stand_when_hit_split_aces_disabled():
    """Verify split Aces each receive exactly 1 card and stand when hit_split_aces is False."""
    rules = TableRules(hit_split_aces=False)
    cards = [
        Card(Suit.CLUBS, Rank.ACE),        # Player 1
        Card(Suit.HEARTS, Rank.SIX),       # Dealer 1
        Card(Suit.SPADES, Rank.ACE),       # Player 2
        Card(Suit.DIAMONDS, Rank.SEVEN),   # Dealer 2
        Card(Suit.HEARTS, Rank.NINE),      # Hand 1 card (A + 9 = 20)
        Card(Suit.SPADES, Rank.EIGHT),     # Hand 2 card (A + 8 = 19)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=50.0)
    engine.submit_action(Action.SPLIT)

    # Both hands should have received their card and automatically stood!
    assert engine.player_hands[0].total == 20
    assert engine.player_hands[0].status == HandStatus.STOOD
    assert engine.player_hands[1].total == 19
    assert engine.player_hands[1].status == HandStatus.STOOD
    assert engine.phase == RoundPhase.DEALER_TURN


def test_split_21_pays_1_to_1_not_bonus():
    """Verify 21 on a split hand pays 1:1, not natural Blackjack bonus."""
    cards = [
        Card(Suit.CLUBS, Rank.ACE),        # Player 1
        Card(Suit.HEARTS, Rank.SIX),       # Dealer 1
        Card(Suit.SPADES, Rank.ACE),       # Player 2
        Card(Suit.DIAMONDS, Rank.SEVEN),   # Dealer 2
        Card(Suit.HEARTS, Rank.KING),      # Hand 1 gets King -> 21!
        Card(Suit.SPADES, Rank.EIGHT),     # Hand 2 gets Eight -> 19
        Card(Suit.CLUBS, Rank.FOUR),       # Dealer draw (6 + 7 + 4 = 17)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=TableRules(hit_split_aces=False), shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=50.0)
    engine.submit_action(Action.SPLIT)
    engine.play_dealer_to_end()
    settlement = engine.settle()

    # Hand 1 has 21, dealer has 17 -> Standard WIN (1:1), not NATURAL_BLACKJACK
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.WIN
    assert settlement.hand_outcomes[0].net_profit == 50.0  # 1:1 payout on $50 bet


def test_double_down_mechanics():
    """Verify Double Down doubles wager, deducts immediately, draws exactly 1 card, and stands."""
    cards = [
        Card(Suit.CLUBS, Rank.FIVE),       # Player 1
        Card(Suit.HEARTS, Rank.SIX),       # Dealer 1
        Card(Suit.SPADES, Rank.SIX),       # Player 2 -> 11
        Card(Suit.DIAMONDS, Rank.SEVEN),   # Dealer 2 -> 13
        Card(Suit.CLUBS, Rank.TEN),        # Player Double card -> 21!
        Card(Suit.HEARTS, Rank.FIVE),      # Dealer hit -> 18
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=50.0)
    assert engine.current_bankroll == 950.0

    state = engine.submit_action(Action.DOUBLE)
    assert engine.current_bankroll == 900.0
    assert state.player_hands[0].bet == 100.0
    assert state.player_hands[0].total == 21
    assert state.player_hands[0].is_doubled
    assert state.phase == RoundPhase.DEALER_TURN

    engine.play_dealer_to_end()
    settlement = engine.settle()

    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.WIN
    assert settlement.hand_outcomes[0].net_profit == 100.0
    assert settlement.gross_return == 200.0
    assert settlement.final_bankroll == 1100.0


def test_double_after_split_restriction():
    """Verify Double is disallowed on split hands when DAS is False."""
    rules = TableRules(double_after_split=False)
    cards = [
        Card(Suit.CLUBS, Rank.EIGHT),
        Card(Suit.HEARTS, Rank.SIX),
        Card(Suit.SPADES, Rank.EIGHT),
        Card(Suit.DIAMONDS, Rank.SEVEN),
        Card(Suit.CLUBS, Rank.THREE),      # Hand 1 gets 3 -> 11
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=50.0)
    engine.submit_action(Action.SPLIT)

    # Hand 1 has 8 + 3 = 11 (2 cards), but DAS is disabled -> DOUBLE must not be legal!
    legal = engine.get_legal_actions()
    assert Action.DOUBLE not in legal

    try:
        engine.submit_action(Action.DOUBLE)
        assert False, "Should raise IllegalActionError"
    except IllegalActionError:
        pass


def test_insurance_win_and_push_main_bet():
    """Verify insurance pays 2:1 when dealer has Natural Blackjack."""
    cards = [
        Card(Suit.CLUBS, Rank.ACE),        # Player 1
        Card(Suit.HEARTS, Rank.ACE),       # Dealer 1 (Ace upcard)
        Card(Suit.SPADES, Rank.KING),      # Player 2 -> Natural BJ!
        Card(Suit.DIAMONDS, Rank.TEN),     # Dealer 2 -> Natural BJ!
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=50.0)
    assert engine.phase == RoundPhase.INSURANCE_OFFERED
    assert engine.current_bankroll == 950.0

    # Accept insurance ($25 deducted)
    state = engine.submit_action if hasattr(engine, "x") else engine.submit_insurance(accept=True)
    assert engine.current_bankroll == 925.0
    assert state.phase == RoundPhase.SETTLEMENT

    settlement = engine.settle()
    # Main bet: Push (both have Natural BJ) -> $50 returned
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.PUSH
    # Insurance: Pays 2:1 + stake returned = $50 + $25 = $75 gross return
    assert settlement.insurance_bet == 25.0
    assert settlement.insurance_payout == 75.0
    assert settlement.gross_return == 125.0  # $50 push + $75 insurance
    assert settlement.net_profit == 50.0     # $50 net profit from insurance
    assert settlement.final_bankroll == 1050.0


def test_surrender_returns_half_bet():
    """Verify surrender returns 50% of the initial wager."""
    cards = [
        Card(Suit.CLUBS, Rank.TEN),        # Player 1
        Card(Suit.HEARTS, Rank.TEN),       # Dealer 1 (10)
        Card(Suit.SPADES, Rank.SIX),       # Player 2 -> 16
        Card(Suit.DIAMONDS, Rank.SEVEN),   # Dealer 2 (7 -> no dealer BJ)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=50.0)
    assert Action.SURRENDER in engine.get_legal_actions()

    state = engine.submit_action(Action.SURRENDER)
    assert state.phase == RoundPhase.SETTLEMENT
    assert state.player_hands[0].is_surrendered

    settlement = engine.settle()
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.SURRENDER
    assert settlement.hand_outcomes[0].payout == 25.0
    assert settlement.hand_outcomes[0].net_profit == -25.0
    assert settlement.gross_return == 25.0
    assert settlement.final_bankroll == 975.0
