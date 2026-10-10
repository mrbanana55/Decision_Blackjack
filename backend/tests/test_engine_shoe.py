"""Unit tests for Shoe mechanics, seeding, penetration, and FIFO injection."""

from app.engine.card import Card, Rank, Suit
from app.engine.interfaces import ShoeEmptyError
from app.engine.shoe import Shoe


def test_shoe_initialization_and_deck_size():
    # 1 deck = 52 cards, 0 burn
    s1 = Shoe(num_decks=1, burn_cards_count=0)
    assert s1.cards_remaining == 52

    # 6 decks = 312 cards, 5 burn
    s6 = Shoe(num_decks=6, burn_cards_count=5)
    assert s6.cards_remaining == 307
    assert len(s6.discards) == 5


def test_seeded_shoe_determinism():
    shoe1 = Shoe(num_decks=6, seed=12345, burn_cards_count=0)
    shoe2 = Shoe(num_decks=6, seed=12345, burn_cards_count=0)

    # Identical seeds must produce identical card sequences
    cards1 = [shoe1.deal() for _ in range(50)]
    cards2 = [shoe2.deal() for _ in range(50)]

    assert cards1 == cards2

    # Different seeds must produce different sequences
    shoe3 = Shoe(num_decks=6, seed=99999, burn_cards_count=0)
    cards3 = [shoe3.deal() for _ in range(50)]
    assert cards1 != cards3


def test_cut_card_penetration_flag():
    # 52 cards, 50% penetration -> cut card at card 26
    shoe = Shoe(num_decks=1, penetration=0.5, burn_cards_count=0)
    assert not shoe.reshuffle_needed

    for _ in range(25):
        shoe.deal()
    assert not shoe.reshuffle_needed

    # Dealing the 26th card crosses the threshold
    shoe.deal()
    assert shoe.reshuffle_needed


def test_fifo_test_card_injection():
    # When test controllers inject cards, they are dealt in exact FIFO order
    c1 = Card(Suit.HEARTS, Rank.ACE)
    c2 = Card(Suit.SPADES, Rank.KING)
    c3 = Card(Suit.CLUBS, Rank.SEVEN)

    shoe = Shoe(num_decks=1, card_sequence=[c1, c2, c3])

    assert shoe.deal() == c1
    assert shoe.deal() == c2
    assert shoe.deal() == c3

    # Subsequent deals fall back to standard shoe cards
    remaining = shoe.deal()
    assert isinstance(remaining, Card)


def test_discard_recovery_when_shoe_depleted():
    c1 = Card(Suit.HEARTS, Rank.TWO)
    c2 = Card(Suit.SPADES, Rank.THREE)

    shoe = Shoe(num_decks=1, card_sequence=[c1, c2])
    # Empty out standard cards to test recovery
    shoe.cards.clear()

    # Deal injected cards
    d1 = shoe.deal()
    d2 = shoe.deal()
    shoe.discard(d1)
    shoe.discard(d2)

    # Dealing when empty shuffles discards
    recovered = shoe.deal()
    assert recovered in [c1, c2]


def test_round_completes_then_reshuffles_next_round():
    """Verify that crossing cut threshold allows round completion then triggers reshuffle."""
    from app.engine.round import BlackjackRound
    from app.engine.rules import TableRules
    from app.engine.types import Action

    # 1 deck, penetration 0.1 -> cut card at card 5
    shoe = Shoe(num_decks=1, penetration=0.1, burn_cards_count=0, seed=42)
    engine = BlackjackRound(rules=TableRules(min_bet=10.0, max_bet=500.0), shoe=shoe)

    # First round deals 4 initial cards + 1 hit = 5 cards -> crosses penetration!
    engine.start_round(bet=20.0)
    if Action.HIT in engine.get_legal_actions():
        engine.submit_action(Action.HIT)
    if Action.STAND in engine.get_legal_actions():
        engine.submit_action(Action.STAND)
    engine.play_dealer_to_end()
    engine.settle()

    # Shoe flagged that reshuffle is needed, and discard tray collected cards
    assert shoe.reshuffle_needed
    assert len(shoe.discards) > 0

    # Next round start automatically triggers shoe.reset()!
    engine.start_round(bet=20.0)
    assert not shoe.reshuffle_needed
    assert shoe.cards_remaining == 52 - len(engine.player_hands[0].cards) - len(engine.dealer_hand.cards)
