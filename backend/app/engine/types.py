from enum import Enum


class _CaseInsensitiveStrEnum(str, Enum):
    """Base string enum supporting case-insensitive comparison."""

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)


class Action(_CaseInsensitiveStrEnum):
    """Permissible player turn actions."""

    HIT = "hit"
    STAND = "stand"
    DOUBLE = "double"
    SPLIT = "split"
    SURRENDER = "surrender"


class RoundPhase(_CaseInsensitiveStrEnum):
    """Sequential lifecycle stages of a single Blackjack round."""

    AWAITING_BET = "awaiting_bet"
    DEALING = "dealing"
    INSURANCE_OFFERED = "insurance_offered"
    DEALER_PEEK = "dealer_peek"
    PLAYER_TURNS = "player_turns"
    DEALER_TURN = "dealer_turn"
    SETTLEMENT = "settlement"
    ROUND_COMPLETE = "round_complete"


class HandStatus(_CaseInsensitiveStrEnum):
    """Current state of an individual hand on the table."""

    ACTIVE = "active"
    STOOD = "stood"
    BUSTED = "busted"
    DOUBLED = "doubled"
    SURRENDERED = "surrendered"
    NATURAL_BLACKJACK = "natural_blackjack"
    SPLIT = "split"


class Soft17Rule(_CaseInsensitiveStrEnum):
    """Dealer rule on Soft 17."""

    STAND_ON_SOFT_17 = "S17"
    HIT_SOFT_17 = "H17"


class DealerStyle(_CaseInsensitiveStrEnum):
    """Hole card dealing and inspection style."""

    AMERICAN_PEEK = "american_peek"
    EUROPEAN_NO_HOLE_CARD = "enhc"


class SurrenderRule(_CaseInsensitiveStrEnum):
    """Table surrender availability."""

    NONE = "none"
    LATE = "late"
    EARLY = "early"


class SettlementOutcome(_CaseInsensitiveStrEnum):
    """Outcome of an individual player hand against the dealer."""

    WIN = "win"
    LOSS = "loss"
    PUSH = "push"
    NATURAL_BLACKJACK = "natural_blackjack"
    SURRENDER = "surrender"
