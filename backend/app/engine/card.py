"""Immutable Card representation and valuation."""

from dataclasses import dataclass
from enum import Enum


class Suit(str, Enum):
    """Playing card suits."""

    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    CLUBS = "clubs"
    SPADES = "spades"

    @property
    def symbol(self) -> str:
        return {
            Suit.HEARTS: "♥",
            Suit.DIAMONDS: "♦",
            Suit.CLUBS: "♣",
            Suit.SPADES: "♠",
        }[self]


class Rank(str, Enum):
    """Playing card ranks."""

    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"


@dataclass(frozen=True, slots=True)
class Card:
    """Immutable playing card with nominal Blackjack value."""

    suit: Suit
    rank: Rank

    @property
    def nominal_value(self) -> int:
        """Nominal Blackjack value (Aces initially evaluate to 11)."""
        if self.rank in {Rank.JACK, Rank.QUEEN, Rank.KING, Rank.TEN}:
            return 10
        if self.rank == Rank.ACE:
            return 11
        return int(self.rank.value)

    @property
    def is_ace(self) -> bool:
        return self.rank == Rank.ACE

    @property
    def code(self) -> str:
        """Short ASCII representation (e.g., '10h', 'As')."""
        return f"{self.rank.value}{self.suit.value[0]}"

    def __str__(self) -> str:
        return f"{self.rank.value}{self.suit.symbol}"

    def __repr__(self) -> str:
        return f"Card({self.rank.value}{self.suit.symbol})"
