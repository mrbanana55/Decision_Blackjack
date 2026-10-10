# Contract Specification: Core Blackjack Engine API

**Feature**: [spec.md](../spec.md)  
**Package**: `backend/app/engine/`  
**Date**: 2026-10-09

## 1. Public Engine Protocols & Interfaces (`interfaces.py`)

### 1.1. `RoundController` Protocol

Defines the contract exposed to test controllers, automated runners, and simulation orchestrators to drive a round from start to finish.

```python
from typing import Protocol, runtime_checkable
from app.engine.types import Action, RoundPhase
from app.engine.round import RoundState, RoundSettlement

@runtime_checkable
class RoundController(Protocol):
    """Programmatic interface for driving a Blackjack round headlessly."""

    @property
    def phase(self) -> RoundPhase:
        """Current lifecycle phase of the round."""
        ...

    @property
    def state(self) -> RoundState:
        """Current immutable snapshot of the entire table/round state."""
        ...

    def start_round(self, bet: float) -> RoundState:
        """Place initial bet, deal initial cards, and advance to next phase.

        Raises:
            InvalidBetError: If bet < min_bet or bet > max_bet.
            InsufficientFundsError: If player bankroll < bet.
            InvalidStateError: If round is not in AWAITING_BET phase.
        """
        ...

    def get_legal_actions(self) -> list[Action]:
        """Return list of valid actions for the currently active player hand.

        Returns empty list if not currently in PLAYER_TURNS phase.
        """
        ...

    def submit_action(self, action: Action) -> RoundState:
        """Apply player action to the currently active hand.

        Raises:
            IllegalActionError: If the action is not in get_legal_actions().
            InvalidStateError: If not in PLAYER_TURNS phase.
            InsufficientFundsError: If doubling/splitting with insufficient bankroll.
        """
        ...

    def submit_insurance(self, accept: bool) -> RoundState:
        """Accept or decline the insurance side bet offer.

        Raises:
            InvalidStateError: If not in INSURANCE_OFFERED phase.
            InsufficientFundsError: If accepting insurance with insufficient bankroll.
        """
        ...

    def play_dealer_to_end(self) -> RoundState:
        """Execute deterministic dealer drawing until reaching terminal state (17+ or bust).

        Raises:
            InvalidStateError: If called before player turns have concluded.
        """
        ...

    def settle(self) -> RoundSettlement:
        """Compare all active hands against dealer, calculate payouts, and finalize bankroll.

        Raises:
            InvalidStateError: If called before dealer turn has concluded.
        """
        ...
```

---

### 1.2. `CardSource` Protocol

Defines the contract for card supply, enabling both standard multi-deck random shoes and pre-arranged test card sequence injection.

```python
from typing import Protocol, runtime_checkable
from app.engine.card import Card

@runtime_checkable
class CardSource(Protocol):
    """Protocol for dealing cards to the round."""

    @property
    def cards_remaining(self) -> int:
        """Count of undealt cards remaining in the shoe."""
        ...

    @property
    def reshuffle_needed(self) -> bool:
        """True if the cut-card penetration threshold has been passed."""
        ...

    def deal(self) -> Card:
        """Deal a single card from the shoe.

        Raises:
            ShoeEmptyError: If no cards remain in shoe or discard tray.
        """
        ...

    def burn(self, count: int) -> list[Card]:
        """Discard the next `count` cards without revealing or putting in play."""
        ...

    def reset(self) -> None:
        """Re-shuffle all cards and reset dealing pointers."""
        ...
```

---

## 2. Domain Exceptions Contract

```python
class EngineError(Exception):
    """Base exception for all blackjack engine errors."""
    pass

class InvalidStateError(EngineError):
    """Raised when an operation is executed during an incompatible round phase."""
    pass

class IllegalActionError(EngineError):
    """Raised when an illegal action is submitted for the active hand."""
    pass

class InvalidBetError(EngineError):
    """Raised when a bet fails minimum/maximum table boundaries."""
    pass

class InsufficientFundsError(EngineError):
    """Raised when attempting a bet, double, split, or insurance exceeding bankroll."""
    pass
```

---

## 3. Serialization Contracts (DTOs)

### `RoundState`
Immutable snapshot dictionary / dataclass:
```json
{
  "phase": "PLAYER_TURNS",
  "active_hand_index": 0,
  "player_hands": [
    {
      "hand_index": 0,
      "cards": [{"suit": "HEARTS", "rank": "EIGHT", "value": 8}, {"suit": "SPADES", "rank": "EIGHT", "value": 8}],
      "bet": 50.0,
      "status": "ACTIVE",
      "total": 16,
      "is_soft": false,
      "is_blackjack": false,
      "is_busted": false,
      "is_split": false,
      "is_doubled": false
    }
  ],
  "dealer_hand": {
    "cards": [{"suit": "CLUBS", "rank": "SIX", "value": 6}],
    "upcard": {"suit": "CLUBS", "rank": "SIX", "value": 6},
    "is_revealed": false,
    "total": 6
  },
  "insurance_bet": 0.0,
  "legal_actions": ["hit", "stand", "double", "split", "surrender"],
  "shoe_cards_remaining": 308,
  "reshuffle_needed": false
}
```
