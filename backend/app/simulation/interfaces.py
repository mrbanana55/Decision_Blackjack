"""Protocols and domain exceptions for the Simulation Orchestrator."""

from typing import Any, Callable, Coroutine, Protocol, runtime_checkable
from app.simulation.types import (
    AgentDecision,
    DecisionContext,
    EntityType,
    SessionStatus,
    SimulationSession,
)


# Domain Exceptions
class SimulationError(Exception):
    """Base exception for all simulation and orchestration errors."""
    pass


class SimulationStateError(SimulationError):
    """Raised when an operation is invalid for the current SessionStatus."""
    pass


class AgentFaultError(SimulationError):
    """Raised when an agent provider encounters a timeout or internal fault."""
    pass


class IllegalAgentActionError(SimulationError):
    """Raised when an agent returns an action that is illegal according to the engine."""
    pass


# Protocols
@runtime_checkable
class DecisionProvider(Protocol):
    """Abstract interface for all blackjack decision agents."""

    @property
    def name(self) -> str:
        """Human-readable identifier of the agent."""
        ...

    @property
    def entity_type(self) -> EntityType:
        """Category of the decision entity (OPTIMAL, JEV, LAYA)."""
        ...

    async def get_decision(self, context: DecisionContext) -> AgentDecision:
        """Produce an action decision given the observable table state."""
        ...


@runtime_checkable
class OrchestratorController(Protocol):
    """Programmatic control interface for managing blackjack simulations."""

    @property
    def status(self) -> SessionStatus:
        """Current lifecycle status of the simulation session."""
        ...

    @property
    def session(self) -> SimulationSession:
        """Current session summary, round counters, and entity metrics."""
        ...

    async def start(self) -> None:
        """Launch the simulation session and execute configured rounds."""
        ...

    async def pause(self) -> None:
        """Suspend execution cleanly at the current turn/round boundary."""
        ...

    async def resume(self) -> None:
        """Resume execution from a paused state."""
        ...

    async def step_round(self) -> None:
        """Advance all active tables by exactly one complete round, then pause."""
        ...

    async def step_turn(self) -> None:
        """Advance active tables by a single decision turn, then pause."""
        ...

    async def retry_failed_entity(self, entity_id: str) -> None:
        """Retry a failed agent turn request after a transient fault and resume."""
        ...

    async def stop(self) -> None:
        """Cancel ongoing execution, finalize metrics, and transition to STOPPED."""
        ...


EventListener = Callable[[Any], Coroutine[Any, Any, None] | None]


@runtime_checkable
class EventPublisher(Protocol):
    """Contract for simulation event subscription and broadcast."""

    def subscribe(self, event_type: Any, listener: EventListener) -> None:
        """Register a callback for a specific event type or all events (if None)."""
        ...

    async def emit(self, event: Any) -> None:
        """Broadcast an event to all registered listeners asynchronously."""
        ...
