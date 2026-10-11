"""Evaluation schemas and comparison data models for Decision Blackjack."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.engine.types import Action


class DecisionCategory(str, Enum):
    """Category of blackjack decision being evaluated."""

    HARD_TOTAL = "hard_total"
    SOFT_TOTAL = "soft_total"
    PAIR_SPLIT = "pair_split"
    SURRENDER = "surrender"
    INSURANCE = "insurance"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass(slots=True, frozen=True)
class DecisionComparison:
    """Evaluation record comparing an agent's turn action against Basic Strategy."""

    is_optimal: bool
    optimal_action: Action
    actual_action: Action
    category: DecisionCategory
    reasoning: str
    is_legal: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class BetComparison:
    """Evaluation record comparing an agent's opening wager against Basic Strategy bet spread."""

    is_bet_optimal: bool
    optimal_bet: float
    actual_bet: float
    bet_delta: float
    true_count: float
    reasoning: str


@dataclass(slots=True, frozen=True)
class BetSpreadConfig:
    """Bet spread configuration based on Hi-Lo True Count."""

    min_bet: float = 50.0
    max_spread_multiplier: int = 12
    num_decks: int = 6
