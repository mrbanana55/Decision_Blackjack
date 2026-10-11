"""Hi-Lo Card Counting model for Blackjack."""

from app.engine.card import Card, Rank


class HiLoCardCounter:
    """Tracks running count, remaining decks, and true count using the Hi-Lo system."""

    def __init__(self, num_decks: int = 6) -> None:
        self.num_decks: int = num_decks
        self.total_cards: int = num_decks * 52
        self.running_count: int = 0
        self.cards_seen: int = 0

    @staticmethod
    def get_card_weight(card: Card) -> int:
        """Calculate Hi-Lo weight for a card: 2-6 is +1, 7-9 is 0, 10-A is -1."""
        if card.rank in (Rank.TWO, Rank.THREE, Rank.FOUR, Rank.FIVE, Rank.SIX):
            return 1
        elif card.rank in (Rank.SEVEN, Rank.EIGHT, Rank.NINE):
            return 0
        else:
            return -1

    def observe_card(self, card: Card) -> None:
        """Observe a single exposed card and update count."""
        self.running_count += self.get_card_weight(card)
        self.cards_seen += 1

    def observe_cards(self, cards: list[Card]) -> None:
        """Observe multiple cards in batch."""
        for card in cards:
            self.observe_card(card)

    @property
    def remaining_decks(self) -> float:
        """Estimate remaining decks to the nearest half deck (min 0.5)."""
        cards_left = max(0, self.total_cards - self.cards_seen)
        decks = cards_left / 52.0
        return max(0.5, round(decks, 1))

    @property
    def true_count(self) -> float:
        """Calculate True Count: running count divided by remaining decks."""
        rem = self.remaining_decks
        if rem <= 0.0:
            return float(self.running_count)
        return round(self.running_count / rem, 1)

    def reset(self) -> None:
        """Reset running count and cards seen when a shoe is reshuffled or replaced."""
        self.running_count = 0
        self.cards_seen = 0
