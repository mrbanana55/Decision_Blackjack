"""Simulation event bus, event types, and event models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import inspect
from typing import Any, Callable, Coroutine
import uuid


class EventType(str, Enum):
    """Enumeration of all observable simulation milestones."""

    SESSION_STARTED = "session_started"
    SESSION_PAUSED = "session_paused"
    SESSION_RESUMED = "session_resumed"
    SESSION_STOPPED = "session_stopped"
    SESSION_COMPLETED = "session_completed"
    SESSION_ERROR = "session_error"

    ROUND_STARTED = "round_started"
    CARD_DEALT = "card_dealt"
    TURN_REQUESTED = "turn_requested"
    DECISION_APPLIED = "decision_applied"
    ROUND_SETTLED = "round_settled"
    SHOE_RESHUFFLED = "shoe_reshuffled"
    ENTITY_ELIMINATED = "entity_eliminated"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.value.lower() == other.lower()
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)


@dataclass
class SimulationEvent:
    """Strongly typed simulation event payload."""

    session_id: str
    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


EventListener = Callable[[SimulationEvent], Coroutine[Any, Any, None] | None]


class EventEmitter:
    """In-memory asynchronous event bus for simulation telemetry and event dispatch."""

    def __init__(self) -> None:
        self._listeners: dict[EventType | None, list[EventListener]] = {}
        self._history: list[SimulationEvent] = []

    @property
    def history(self) -> list[SimulationEvent]:
        """Chronological list of all emitted events."""
        return list(self._history)

    def subscribe(self, event_type: EventType | None, listener: EventListener) -> None:
        """Register a callback for a specific event type, or all events if None."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: EventType | None, listener: EventListener) -> None:
        """Unregister a previously registered callback."""
        if event_type in self._listeners and listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)

    async def emit(self, event: SimulationEvent) -> None:
        """Broadcast a simulation event to all registered listeners asynchronously.
        
        Preserves chronological ordering in internal history and supports both sync
        and async listener callbacks.
        """
        self._history.append(event)

        # Collect applicable listeners: exact match listeners + wildcard (None) listeners
        callbacks: list[EventListener] = []
        if event.event_type in self._listeners:
            callbacks.extend(self._listeners[event.event_type])
        if None in self._listeners:
            callbacks.extend(self._listeners[None])

        for callback in callbacks:
            try:
                res = callback(event)
                if inspect.isawaitable(res):
                    await res
            except Exception:
                # Listener exceptions must not interrupt event publishing to other listeners
                pass

    def clear(self) -> None:
        """Clear all registered listeners and event history."""
        self._listeners.clear()
        self._history.clear()
