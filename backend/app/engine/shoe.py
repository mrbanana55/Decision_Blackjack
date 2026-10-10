"""Deterministic multi-deck Card Shoe with seeded shuffling, burn cards, and test injection."""

import random
from app.engine.card import Card, Rank, Suit
from app.engine.interfaces import ShoeEmptyError


class Shoe:
    """Multi-deck card shoe conforming to CardSource protocol."""

    def __init__(
        self,
        num_decks: int = 6,
        seed: int | None = None,
        penetration: float = 0.75,
        burn_cards_count: int = 0,
        card_sequence: list[Card] | None = None,
    ) -> None:
        if num_decks < 1 or num_decks > 8:
            raise ValueError("Shoe must contain between 1 and 8 decks.")
        if penetration <= 0.0 or penetration > 1.0:
            raise ValueError("Penetration must be between 0.0 and 1.0.")

        self.num_decks: int = num_decks
        self.seed: int | None = seed
        self.penetration: float = penetration
        self.burn_cards_count: int = burn_cards_count
        self.rng: random.Random = random.Random(seed)

        self.injected_sequence: list[Card] = list(card_sequence) if card_sequence else []
        self.cards: list[Card] = []
        self.discards: list[Card] = []
        self.cards_dealt_count: int = 0
        self.cut_card_index: int = 0
        self.reshuffle_needed: bool = False

        self.reset()

    def _build_decks(self) -> list[Card]:
        """Generate fresh undealt decks."""
        full_shoe: list[Card] = []
        for _ in range(self.num_decks):
            for suit in Suit:
                for rank in Rank:
                    full_shoe.append(Card(suit=suit, rank=rank))
        return full_shoe

    def reset(self) -> None:
        """Re-initialize and shuffle all cards in the shoe."""
        self.cards = self._build_decks()
        self.discards.clear()
        self.cards_dealt_count = 0
        self.reshuffle_needed = False

        # Deterministic Fisher-Yates shuffle
        self.rng.shuffle(self.cards)

        total_cards = len(self.cards)
        self.cut_card_index = int(total_cards * self.penetration)

        # Discard burn cards upon shoe initialization
        if self.burn_cards_count > 0:
            self.burn(self.burn_cards_count)

    @property
    def cards_remaining(self) -> int:
        """Count of undealt cards remaining."""
        return len(self.injected_sequence) + len(self.cards)

    def deal(self) -> Card:
        """Deal a single card from the shoe (FIFO injected first, then main shoe)."""
        if self.injected_sequence:
            return self.injected_sequence.pop(0)

        if not self.cards:
            if self.discards:
                # Recover and shuffle discard tray mid-round if cards are completely exhausted
                self.cards = list(self.discards)
                self.discards.clear()
                self.rng.shuffle(self.cards)
            else:
                raise ShoeEmptyError("No cards remaining in shoe or discard tray.")

        card = self.cards.pop()
        self.cards_dealt_count += 1

        if self.cards_dealt_count >= self.cut_card_index:
            self.reshuffle_needed = True

        return card

    def burn(self, count: int) -> list[Card]:
        """Discard the next `count` cards directly into the discard tray."""
        burned: list[Card] = []
        for _ in range(count):
            if self.cards:
                card = self.cards.pop()
                self.discards.append(card)
                self.cards_dealt_count += 1
                burned.append(card)
        return burned

    def discard(self, card: Card) -> None:
        """Place a card into the discard tray."""
        self.discards.append(card)

    def discard_many(self, cards: list[Card]) -> None:
        """Place multiple cards into the discard tray."""
        self.discards.extend(cards)

    def __len__(self) -> int:
        return self.cards_remaining
