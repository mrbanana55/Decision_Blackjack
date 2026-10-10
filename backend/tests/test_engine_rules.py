"""Unit tests verifying configurable casino rules and illegal action validation."""

from app.engine.card import Card, Rank, Suit
from app.engine.interfaces import IllegalActionError, InvalidStateError
from app.engine.round import BlackjackRound
from app.engine.rules import TableRules
from app.engine.shoe import Shoe
from app.engine.types import (
    Action,
    DealerStyle,
    HandStatus,
    RoundPhase,
    SettlementOutcome,
    Soft17Rule,
)


def test_soft_17_dealer_stands_on_s17():
    """Verify dealer stands on Soft 17 under S17 rules."""
    rules = TableRules(soft_17_rule=Soft17Rule.STAND_ON_SOFT_17)
    cards = [
        Card(Suit.CLUBS, Rank.TEN),       # Player 1
        Card(Suit.HEARTS, Rank.ACE),      # Dealer 1 (Ace)
        Card(Suit.SPADES, Rank.NINE),     # Player 2 -> 19
        Card(Suit.DIAMONDS, Rank.SIX),    # Dealer 2 (6 -> Soft 17)
        Card(Suit.CLUBS, Rank.FIVE),      # Extra card in shoe (should not be drawn!)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

    # Note: Dealer upcard is Ace, insurance offered
    engine.start_round(bet=50.0)
    assert engine.phase == RoundPhase.INSURANCE_OFFERED
    engine.submit_insurance(accept=False)

    # Player stands on 19
    engine.submit_action(Action.STAND)

    # Dealer turn
    state = engine.play_dealer_to_end()
    assert state.dealer_hand.total == 17
    assert state.dealer_hand.is_soft
    assert len(state.dealer_hand.cards) == 2  # Did not draw extra card!

    settlement = engine.settle()
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.WIN
    assert settlement.hand_outcomes[0].net_profit == 50.0


def test_soft_17_dealer_hits_on_h17():
    """Verify dealer hits Soft 17 under H17 rules until Hard 17+ or bust."""
    rules = TableRules(soft_17_rule=Soft17Rule.HIT_SOFT_17)
    cards = [
        Card(Suit.CLUBS, Rank.TEN),       # Player 1
        Card(Suit.HEARTS, Rank.ACE),      # Dealer 1 (Ace)
        Card(Suit.SPADES, Rank.NINE),     # Player 2 -> 19
        Card(Suit.DIAMONDS, Rank.SIX),    # Dealer 2 (6 -> Soft 17)
        Card(Suit.CLUBS, Rank.THREE),     # Dealer Hit on Soft 17 -> A + 6 + 3 = Soft 20!
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

    engine.start_round(bet=50.0)
    engine.submit_insurance(accept=False)
    engine.submit_action(Action.STAND)

    state = engine.play_dealer_to_end()
    assert state.dealer_hand.total == 20
    assert len(state.dealer_hand.cards) == 3

    settlement = engine.settle()
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.LOSS
    assert settlement.hand_outcomes[0].net_profit == -50.0


def test_blackjack_payout_ratios():
    """Verify 3:2, 6:5, and 1:1 payout arithmetic on Natural Blackjack."""
    ratios_and_expected = [
        (1.5, 75.0, 125.0),   # 3:2 on $50 -> profit $75, gross $125
        (1.2, 60.0, 110.0),   # 6:5 on $50 -> profit $60, gross $110
        (1.0, 50.0, 100.0),   # 1:1 on $50 -> profit $50, gross $100
    ]

    for ratio, expected_profit, expected_gross in ratios_and_expected:
        rules = TableRules(blackjack_payout_ratio=ratio)
        cards = [
            Card(Suit.CLUBS, Rank.ACE),       # Player 1
            Card(Suit.HEARTS, Rank.FIVE),     # Dealer 1 (5 -> no peek)
            Card(Suit.SPADES, Rank.KING),     # Player 2 -> Natural BJ!
            Card(Suit.DIAMONDS, Rank.EIGHT),  # Dealer 2
        ]
        shoe = Shoe(card_sequence=cards)
        engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

        engine.start_round(bet=50.0)
        assert engine.phase == RoundPhase.SETTLEMENT
        settlement = engine.settle()

        assert settlement.hand_outcomes[0].outcome == SettlementOutcome.NATURAL_BLACKJACK
        assert settlement.hand_outcomes[0].net_profit == expected_profit
        assert settlement.gross_return == expected_gross


def test_american_peek_dealer_blackjack_resolves_immediately():
    """Verify American Peek terminates round immediately if dealer has Natural BJ."""
    rules = TableRules(hole_card_rule=DealerStyle.AMERICAN_PEEK)
    cards = [
        Card(Suit.CLUBS, Rank.TEN),       # Player 1 (10)
        Card(Suit.HEARTS, Rank.KING),     # Dealer 1 (10-value upcard)
        Card(Suit.SPADES, Rank.NINE),     # Player 2 (9 -> 19)
        Card(Suit.DIAMONDS, Rank.ACE),    # Dealer 2 (Ace -> Natural BJ!)
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

    state = engine.start_round(bet=50.0)
    # Peek detected BJ immediately -> phase moves straight to SETTLEMENT
    assert state.phase == RoundPhase.SETTLEMENT
    assert state.dealer_hand.is_revealed
    assert state.dealer_hand.is_blackjack
    assert engine.get_legal_actions() == []

    settlement = engine.settle()
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.LOSS
    assert settlement.hand_outcomes[0].net_profit == -50.0
    assert engine.current_bankroll == 950.0


def test_enhc_dealing_and_total_bets_lost():
    """Verify ENHC defers dealer second card and applies Total Bets Lost on Double Down."""
    rules = TableRules(hole_card_rule=DealerStyle.EUROPEAN_NO_HOLE_CARD)
    cards = [
        Card(Suit.CLUBS, Rank.FIVE),      # Player 1 (5)
        Card(Suit.HEARTS, Rank.TEN),      # Dealer 1 (10) - ONLY 1 card dealt to dealer!
        Card(Suit.SPADES, Rank.SIX),      # Player 2 (6 -> total 11)
        Card(Suit.CLUBS, Rank.EIGHT),     # Player Double Down card (8 -> total 19)
        Card(Suit.DIAMONDS, Rank.ACE),    # Dealer draws 2nd card in Dealer Turn -> Natural BJ!
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=rules, shoe=shoe, player_bankroll=1000.0)

    state = engine.start_round(bet=50.0)
    assert len(state.dealer_hand.cards) == 1
    assert state.phase == RoundPhase.PLAYER_TURNS

    # Double Down
    state = engine.submit_action(Action.DOUBLE)
    assert engine.current_bankroll == 900.0  # $50 initial + $50 double immediately deducted
    assert state.player_hands[0].bet == 100.0
    assert state.player_hands[0].total == 19
    assert engine.phase == RoundPhase.DEALER_TURN

    # Dealer plays and draws second card (Ace -> Natural BJ!)
    state = engine.play_dealer_to_end()
    assert state.dealer_hand.is_blackjack
    assert len(state.dealer_hand.cards) == 2

    # Settlement: TBL forfeits the entire $100
    settlement = engine.settle()
    assert settlement.hand_outcomes[0].outcome == SettlementOutcome.LOSS
    assert settlement.hand_outcomes[0].net_profit == -100.0
    assert settlement.gross_return == 0.0
    assert settlement.final_bankroll == 900.0


def test_action_validation_rejections():
    """Verify invalid actions raise IllegalActionError and InvalidStateError without side effects."""
    cards = [
        Card(Suit.CLUBS, Rank.SEVEN),
        Card(Suit.HEARTS, Rank.SIX),
        Card(Suit.SPADES, Rank.FIVE),
        Card(Suit.DIAMONDS, Rank.SEVEN),
        Card(Suit.CLUBS, Rank.TWO),
    ]
    shoe = Shoe(card_sequence=cards)
    engine = BlackjackRound(rules=TableRules(), shoe=shoe, player_bankroll=1000.0)

    # 1. Action before round start
    try:
        engine.submit_action(Action.HIT)
        assert False, "Should raise InvalidStateError"
    except InvalidStateError:
        pass

    engine.start_round(bet=50.0)

    # 2. Split when not holding a pair
    assert Action.SPLIT not in engine.get_legal_actions()
    try:
        engine.submit_action(Action.SPLIT)
        assert False, "Should raise IllegalActionError"
    except IllegalActionError:
        pass

    # 3. Hit (cards now: 7 + 5 + 2 = 14, 3 cards)
    engine.submit_action(Action.HIT)
    assert len(engine.player_hands[0].cards) == 3

    # 4. Double after Hit (illegal, hand length is 3)
    assert Action.DOUBLE not in engine.get_legal_actions()
    try:
        engine.submit_action(Action.DOUBLE)
        assert False, "Should raise IllegalActionError"
    except IllegalActionError:
        pass

    # Bankroll still intact at 950
    assert engine.current_bankroll == 950.0
    assert engine.phase == RoundPhase.PLAYER_TURNS
