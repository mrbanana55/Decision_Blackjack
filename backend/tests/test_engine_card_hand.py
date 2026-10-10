"""Unit tests for Card and Hand domain entities."""

from app.engine.card import Card, Rank, Suit
from app.engine.hand import DealerHand, Hand, HandValue, PlayerHand
from app.engine.types import HandStatus


def test_card_properties():
    c2 = Card(Suit.HEARTS, Rank.TWO)
    assert c2.nominal_value == 2
    assert not c2.is_ace
    assert str(c2) == "2♥"

    ck = Card(Suit.SPADES, Rank.KING)
    assert ck.nominal_value == 10
    assert not ck.is_ace

    ca = Card(Suit.DIAMONDS, Rank.ACE)
    assert ca.nominal_value == 11
    assert ca.is_ace


def test_hard_hand_evaluation():
    hand = Hand()
    hand.add_card(Card(Suit.CLUBS, Rank.TEN))
    hand.add_card(Card(Suit.HEARTS, Rank.SIX))

    val = hand.evaluate()
    assert val.total == 16
    assert not val.is_soft
    assert not val.is_busted
    assert not val.is_blackjack


def test_soft_hand_evaluation():
    hand = Hand()
    hand.add_card(Card(Suit.CLUBS, Rank.ACE))
    hand.add_card(Card(Suit.HEARTS, Rank.SIX))

    val = hand.evaluate()
    assert val.total == 17
    assert val.is_soft
    assert not val.is_busted


def test_multiple_aces_softness_reduction():
    hand = Hand()
    hand.add_card(Card(Suit.CLUBS, Rank.ACE))
    hand.add_card(Card(Suit.HEARTS, Rank.ACE))
    # A + A = 12 (one counted as 11, one as 1)
    val = hand.evaluate()
    assert val.total == 12
    assert val.is_soft

    # Add a 9 -> 12 + 9 = 21 soft
    hand.add_card(Card(Suit.SPADES, Rank.NINE))
    val = hand.evaluate()
    assert val.total == 21
    assert val.is_soft

    # Add a 2 -> 21 + 2 = 23 -> reduce the remaining soft ace to 1 -> total 13 hard
    hand.add_card(Card(Suit.DIAMONDS, Rank.TWO))
    val = hand.evaluate()
    assert val.total == 13
    assert not val.is_soft
    assert not val.is_busted


def test_natural_blackjack_vs_other_21():
    # Natural Blackjack (2 cards: Ace + 10-value)
    bj_hand = PlayerHand(bet=50.0)
    bj_hand.add_card(Card(Suit.CLUBS, Rank.ACE))
    bj_hand.add_card(Card(Suit.HEARTS, Rank.KING))
    val = bj_hand.evaluate()
    assert val.total == 21
    assert val.is_blackjack
    assert bj_hand.status == HandStatus.NATURAL_BLACKJACK

    # 3-card 21 (7 + 7 + 7)
    three_card_hand = PlayerHand(bet=50.0)
    three_card_hand.add_card(Card(Suit.CLUBS, Rank.SEVEN))
    three_card_hand.add_card(Card(Suit.HEARTS, Rank.SEVEN))
    three_card_hand.add_card(Card(Suit.SPADES, Rank.SEVEN))
    val3 = three_card_hand.evaluate()
    assert val3.total == 21
    assert not val3.is_blackjack

    # Split 21 (is_split=True, A + K)
    split_hand = PlayerHand(bet=50.0, is_split=True)
    split_hand.add_card(Card(Suit.CLUBS, Rank.ACE))
    split_hand.add_card(Card(Suit.HEARTS, Rank.KING))
    val_split = split_hand.evaluate()
    assert val_split.total == 21
    assert not val_split.is_blackjack  # Split 21 is NOT a natural blackjack!


def test_bust_detection():
    hand = Hand()
    hand.add_card(Card(Suit.CLUBS, Rank.TEN))
    hand.add_card(Card(Suit.HEARTS, Rank.SEVEN))
    hand.add_card(Card(Suit.SPADES, Rank.EIGHT))  # Total 25

    val = hand.evaluate()
    assert val.total == 25
    assert val.is_busted


def test_dealer_hand_upcard_and_reveal():
    dealer = DealerHand()
    c_up = Card(Suit.SPADES, Rank.ACE)
    c_hole = Card(Suit.HEARTS, Rank.NINE)

    dealer.add_card(c_up)
    dealer.add_card(c_hole)

    assert not dealer.is_revealed
    assert dealer.upcard == c_up
    assert dealer.hole_card == c_hole
    # When not revealed, visible total evaluates upcard only
    assert dealer.visible_total == 11

    dealer.reveal()
    assert dealer.is_revealed
    assert dealer.evaluate().total == 20
