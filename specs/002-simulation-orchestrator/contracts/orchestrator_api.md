# Contract Specification: Simulation Orchestrator API

**Feature**: [spec.md](../spec.md)  
**Package**: `backend/app/simulation/`  
**Date**: 2026-10-10

---

## 1. Protocols & Public Interfaces (`interfaces.py`)

### 1.1. `DecisionProvider` Protocol

Contract governing all decision entities (fake test agents, basic strategy, and future real LLM/local model providers):

```python
from typing import Protocol, runtime_checkable
from app.simulation.types import AgentDecision, DecisionContext, EntityType

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
        """Produce an action decision given the observable table state.
        
        Raises:
            AgentTimeoutError: If inference exceeds maximum allowed duration.
            AgentExecutionError: If provider encounters an unhandled internal exception.
        """
        ...
```

---

### 1.2. `OrchestratorController` Protocol

Contract exposed to test controllers, automated runners, and simulation orchestrators:

```python
from typing import Protocol, runtime_checkable
from app.simulation.types import SessionStatus, SimulationConfig, SimulationSession

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
        """Launch the simulation session and execute configured rounds.
        
        Raises:
            SimulationStateError: If simulation is already running or completed.
        """
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
```

---

### 1.3. `EventEmitter` Contract

Event bus protocol allowing downstream persistence, file loggers, and WebSocket telemetry to observe the simulation:

```python
from typing import Callable, Coroutine, Protocol, Any
from app.simulation.events import EventType, SimulationEvent

EventListener = Callable[[SimulationEvent], Coroutine[Any, Any, None] | None]

class EventPublisher(Protocol):
    """Contract for simulation event subscription and broadcast."""

    def subscribe(self, event_type: EventType | None, listener: EventListener) -> None:
        """Register a callback for a specific event type or all events (if None)."""
        ...

    async def emit(self, event: SimulationEvent) -> None:
        """Broadcast an event to all registered listeners asynchronously."""
        ...
```

---

## 2. Event Payload Schema

All emitted events follow a structured, strongly typed schema:

```json
{
  "event_id": "evt-7f8e3d2a-1b0c",
  "session_id": "sim-9a1b2c3d",
  "event_type": "DECISION_APPLIED",
  "timestamp": "2026-10-10T19:00:00.123456Z",
  "payload": {
    "round_number": 42,
    "entity_id": "jev",
    "entity_type": "JEV",
    "hand_index": 0,
    "action": "hit",
    "confidence": 0.89,
    "latency_ms": 145.2,
    "reasoning": "Dealer upcard is 7, player total is 16 with no Ace. Basic strategy dictates hit.",
    "resulting_total": 21,
    "resulting_status": "active"
  }
}
```

---

## 3. Domain Exceptions Contract

```python
class SimulationError(Exception):
    """Base exception for all simulation and orchestration errors."""
    pass

class SimulationStateError(SimulationError):
    """Raised when an operation is invalid for the current SessionStatus."""
    pass

class AgentFaultError(SimulationError):
    """Raised when an agent provider times out or throws an unhandled exception."""
    pass

class IllegalAgentActionError(SimulationError):
    """Raised when an agent returns an action that is illegal according to the engine."""
    pass
```
