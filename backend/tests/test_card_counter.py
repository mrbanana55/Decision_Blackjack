"""Unit tests for Hi-Lo card counter."""

from app.engine.card import Card, Rank, Suit
from app.models.card_counter import HiLoCardCounter


def _card(rank: Rank) -> Card:
    return Card(suit=Suit.HEARTS, rank=rank)


def test_hilo_card_values():
    """Verify standard Hi-Lo values: 2-6 (+1), 7-9 (0), 10-A (-1)."""
    counter = HiLoCardCounter(num_decks=6)

    # Low cards (+1)
    for rank in (Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX):
        assert counter.get_card_weight(_card(rank)) == 1

    # Neutral cards (0)
    for rank in (Rank.SEVEN, Rank.EIGHT, Rank.NINE):
        assert counter.get_card_weight(_card(rank)) == 0

    # High cards (-1)
    for rank in (Rank.TEN, Rank.JACK, Rank.QUEEN, Rank.KING, Rank.ACE):
        assert counter.get_card_weight(_card(rank)) == -1


def test_running_and_true_count_progression():
    """Verify running count and true count updates."""
    counter = HiLoCardCounter(num_decks=6)
    assert counter.running_count == 0
    assert counter.true_count == 0.0

    # Observe 10 low cards (+10 running count)
    cards = [_card(Rank.FIVE) for _ in range(10)]
    counter.observe_cards(cards)

    assert counter.running_count == 10
    assert counter.cards_seen == 10
    # Remaining decks ~ (312 - 10) / 52 = 5.8 decks -> TC ~ 10 / 5.8 = 1.7
    assert counter.true_count == 1.7


def test_remaining_deck_minimum_clamp():
    """Verify remaining deck estimation clamps to minimum 0.5 decks."""
    counter = HiLoCardCounter(num_decks=1)
    # Observe 50 cards out of 52
    counter.observe_cards([_card(Rank.ACE) for _ in range(50)])
    assert counter.remaining_decks >= 0.5


def test_counter_reset():
    """Verify count reset upon shoe reshuffle/adoption."""
    counter = HiLoCardCounter(num_decks=6)
    counter.observe_cards([_card(Rank.TWO), _card(Rank.THREE)])
    assert counter.running_count == 2
    assert counter.cards_seen == 2

    counter.reset()
    assert counter.running_count == 0
    assert counter.cards_seen == 0
    assert counter.true_count == 0.0


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All card counter tests passed!")
