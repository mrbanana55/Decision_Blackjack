"""Core deterministic Blackjack engine package."""

from app.engine.card import Card, Rank, Suit
from app.engine.hand import DealerHand, Hand, HandValue, PlayerHand
from app.engine.interfaces import (
    CardSource,
    EngineError,
    IllegalActionError,
    InsufficientFundsError,
    InvalidBetError,
    InvalidStateError,
    RoundController,
    RoundEventListener,
    ShoeEmptyError,
)
from app.engine.round import BlackjackRound, RoundState
from app.engine.rules import TableRules
from app.engine.settlement import HandSettlement, RoundSettlement, settle_round
from app.engine.shoe import Shoe
from app.engine.types import (
    Action,
    DealerStyle,
    HandStatus,
    RoundPhase,
    SettlementOutcome,
    Soft17Rule,
    SurrenderRule,
)

__version__ = "0.1.0"

__all__ = [
    # Core orchestration
    "BlackjackRound",
    "RoundState",
    "TableRules",
    "Shoe",
    "settle_round",
    "HandSettlement",
    "RoundSettlement",
    # Primitives & Entities
    "Card",
    "Suit",
    "Rank",
    "Hand",
    "PlayerHand",
    "DealerHand",
    "HandValue",
    # Enums & Types
    "Action",
    "RoundPhase",
    "HandStatus",
    "Soft17Rule",
    "DealerStyle",
    "SurrenderRule",
    "SettlementOutcome",
    # Protocols
    "CardSource",
    "RoundController",
    "RoundEventListener",
    # Exceptions
    "EngineError",
    "InvalidStateError",
    "IllegalActionError",
    "InvalidBetError",
    "InsufficientFundsError",
    "ShoeEmptyError",
]
