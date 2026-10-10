"""Abstract protocols and domain exceptions for the Blackjack engine."""

from typing import Any, Protocol, runtime_checkable
from app.engine.types import Action, RoundPhase


# Domain Exceptions
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


class ShoeEmptyError(EngineError):
    """Raised when no cards remain in the shoe or discard tray."""
    pass


# Protocols
@runtime_checkable
class CardSource(Protocol):
    """Contract for card supply and dealing."""

    @property
    def cards_remaining(self) -> int:
        """Count of undealt cards remaining in the shoe."""
        ...

    @property
    def reshuffle_needed(self) -> bool:
        """True if the cut-card penetration threshold has been passed."""
        ...

    def deal(self) -> Any:
        """Deal a single card."""
        ...

    def burn(self, count: int) -> list[Any]:
        """Discard the next `count` cards."""
        ...

    def reset(self) -> None:
        """Re-shuffle all cards and reset dealing pointers."""
        ...


@runtime_checkable
class RoundController(Protocol):
    """Contract for headless test controllers and simulation orchestrators."""

    @property
    def phase(self) -> RoundPhase:
        """Current lifecycle phase of the round."""
        ...

    @property
    def state(self) -> Any:
        """Current immutable snapshot of the entire table/round state."""
        ...

    def start_round(self, bet: float) -> Any:
        """Place initial bet and deal initial cards."""
        ...

    def get_legal_actions(self) -> list[Action]:
        """Return list of valid actions for the currently active player hand."""
        ...

    def submit_action(self, action: Action) -> Any:
        """Apply player action to the currently active hand."""
        ...

    def submit_insurance(self, accept: bool) -> Any:
        """Accept or decline the insurance side bet offer."""
        ...

    def play_dealer_to_end(self) -> Any:
        """Execute deterministic dealer drawing until reaching terminal state."""
        ...

    def settle(self) -> Any:
        """Compare all active hands against dealer, calculate payouts, and finalize bankroll."""
        ...


@runtime_checkable
class RoundEventListener(Protocol):
    """Observer protocol for round events and telemetry dispatch."""

    def on_phase_change(self, old_phase: RoundPhase, new_phase: RoundPhase) -> None:
        ...

    def on_card_dealt(self, target: str, card: Any) -> None:
        ...

    def on_action_applied(self, action: Action, hand_index: int) -> None:
        ...
