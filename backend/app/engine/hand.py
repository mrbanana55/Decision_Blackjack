"""Hand representations, score calculation, Ace softness, and natural 21 evaluation."""

from dataclasses import dataclass
from app.engine.card import Card
from app.engine.types import HandStatus


@dataclass(frozen=True, slots=True)
class HandValue:
    """Calculated total and status flags for a hand."""

    total: int
    is_soft: bool
    is_busted: bool
    is_blackjack: bool


class Hand:
    """Base class for player and dealer card collections."""

    def __init__(self, cards: list[Card] | None = None) -> None:
        self.cards: list[Card] = list(cards) if cards else []
        self.status: HandStatus = HandStatus.ACTIVE
        self.is_split: bool = False
        self.is_doubled: bool = False
        self.is_surrendered: bool = False

    def add_card(self, card: Card) -> None:
        """Add a card to the hand and update evaluation state."""
        self.cards.append(card)
        self.evaluate()

    def evaluate(self) -> HandValue:
        """Calculate dynamic total, Ace softness reduction, and bust/blackjack flags."""
        total = sum(c.nominal_value for c in self.cards)
        soft_aces = sum(1 for c in self.cards if c.is_ace)

        # Reduce Aces from 11 to 1 as needed to avoid busting
        while total > 21 and soft_aces > 0:
            total -= 10
            soft_aces -= 1

        is_soft = soft_aces > 0
        is_busted = total > 21
        is_blackjack = (
            len(self.cards) == 2
            and total == 21
            and not self.is_split
        )

        if is_busted:
            self.status = HandStatus.BUSTED
        elif is_blackjack and self.status == HandStatus.ACTIVE:
            self.status = HandStatus.NATURAL_BLACKJACK

        return HandValue(
            total=total,
            is_soft=is_soft,
            is_busted=is_busted,
            is_blackjack=is_blackjack,
        )

    @property
    def total(self) -> int:
        return self.evaluate().total

    @property
    def is_busted(self) -> bool:
        return self.evaluate().is_busted

    @property
    def is_blackjack(self) -> bool:
        return self.evaluate().is_blackjack

    @property
    def is_soft(self) -> bool:
        return self.evaluate().is_soft

    def __len__(self) -> int:
        return len(self.cards)

    def __repr__(self) -> str:
        cards_repr = ", ".join(str(c) for c in self.cards)
        return f"{self.__class__.__name__}([{cards_repr}], total={self.total}, status={self.status.value})"


class PlayerHand(Hand):
    """Player hand on the table with wager tracking."""

    def __init__(
        self,
        bet: float = 0.0,
        cards: list[Card] | None = None,
        hand_index: int = 0,
        is_split: bool = False,
    ) -> None:
        super().__init__(cards=cards)
        self.bet: float = float(bet)
        self.hand_index: int = hand_index
        self.is_split: bool = is_split
        if self.cards:
            self.evaluate()

    @property
    def can_split(self) -> bool:
        """Check if initial two cards have matching rank or nominal value."""
        if len(self.cards) != 2:
            return False
        # Matches if rank matches or both are 10-value cards
        return (
            self.cards[0].rank == self.cards[1].rank
            or self.cards[0].nominal_value == self.cards[1].nominal_value == 10
        )


class DealerHand(Hand):
    """Dealer hand on the table with hole card hiding and revealing."""

    def __init__(self, cards: list[Card] | None = None) -> None:
        super().__init__(cards=cards)
        self.is_revealed: bool = False

    @property
    def upcard(self) -> Card | None:
        """The visible face-up card."""
        return self.cards[0] if len(self.cards) >= 1 else None

    @property
    def hole_card(self) -> Card | None:
        """The hidden face-down card."""
        return self.cards[1] if len(self.cards) >= 2 else None

    @property
    def visible_total(self) -> int:
        """Visible points on table (upcard only if hole card hidden)."""
        if self.is_revealed or len(self.cards) <= 1:
            return self.total
        return self.upcard.nominal_value if self.upcard else 0

    def reveal(self) -> None:
        """Reveal dealer hole card."""
        self.is_revealed = True
        self.evaluate()
