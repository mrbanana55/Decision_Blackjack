# Interface Contract: Persistence Service & Telemetry Listener

**Feature**: `specs/004-database-persistence` | **Date**: 2026-10-11

This contract documents the public interfaces exposed by the `backend/app/persistence` package to the simulation orchestrator, API routes, and analytics layer.

---

## 1. Database Connection & Lifecycle Contract

`backend/app/persistence/database.py`

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

def get_engine() -> AsyncEngine:
    """Returns the singleton pooled async SQLAlchemy engine."""
    ...

def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Returns the async sessionmaker factory."""
    ...

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    ...

async def init_db(engine: AsyncEngine | None = None) -> None:
    """Provisions missing tables and ENUMs via Base.metadata.create_all."""
    ...

async def check_db_health(engine: AsyncEngine | None = None) -> bool:
    """Executes a simple SELECT 1 query to verify PostgreSQL connectivity."""
    ...
```

---

## 2. Telemetry Persistence Listener Contract

`backend/app/persistence/listener.py`

Subscribes to orchestrator events without blocking simulation execution.

```python
from uuid import UUID
from backend.app.simulation.events import EventEmitter, SimulationEvent

class SimulationPersistenceListener:
    """Listens to simulation events and persists them to PostgreSQL."""

    def __init__(
        self,
        run_id: UUID,
        event_emitter: EventEmitter,
        batch_rounds: int = 1,
    ) -> None:
        """Initialize listener attached to an EventEmitter and run ID.
        
        Args:
            run_id: The active experiment Run UUID.
            event_emitter: The orchestrator's event dispatcher.
            batch_rounds: Number of completed rounds before committing (1 = per-round atomic flush).
        """
        ...

    def attach(self) -> None:
        """Register listeners for orchestrator event types."""
        ...

    def detach(self) -> None:
        """Unsubscribe from event emitter."""
        ...

    async def flush(self) -> None:
        """Explicitly flush any pending in-memory buffered records to the database."""
        ...

    async def handle_event(self, event: SimulationEvent) -> None:
        """Route event (e.g. CARD_DEALT, DECISION_APPLIED, ROUND_COMPLETED) to buffer."""
        ...
```

### Event Mappings to Relational Entities

| Simulation Event | Database Operation |
|---|---|
| `SIMULATION_STARTED` | Creates `SIMULATION`, `PLAYER_SESSION` (Jev, Laya, Optimal). |
| `SHOE_GENERATED` | Inserts `SHOE`, initializes `PLAYER_SHOE_STATE` for each player. |
| `ROUND_STARTED` | Inserts `ROUND`, `ROUND_PLAYER` records; records opening `BET`. |
| `CARD_DEALT` | Appends `CARD_EVENT` with sequential number and shoe position. |
| `DECISION_APPLIED` | Inserts `DECISION` (with `optimal_reference_action`), creates `MODEL_RESPONSE` if AI. |
| `ROUND_COMPLETED` | Inserts `HAND_RESULT`, `BANKROLL_TRANSACTION`, updates bankrolls; commits transaction. |
| `SIMULATION_COMPLETED`| Updates `SIMULATION.status = 'COMPLETED'`, records final bankroll. |

---

## 3. Run & Analytics Repository Contract

`backend/app/persistence/repositories.py`

```python
from uuid import UUID
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.persistence.models import Run, Simulation, Round

class RunRepository:
    """Data access repository for simulation experiments and historical replays."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, config_dict: dict[str, Any]) -> Run:
        """Create a new Run and its immutable RunConfiguration snapshot."""
        ...

    async def get_run(self, run_id: UUID) -> Run | None:
        """Retrieve a Run with its configuration and simulation summaries."""
        ...

    async def list_runs(self, limit: int = 50, offset: int = 0) -> list[Run]:
        """List past runs ordered by created_at descending."""
        ...

    async def delete_run(self, run_id: UUID) -> bool:
        """Cascading-delete a Run and all its descendant records."""
        ...

    async def get_round_replay(self, round_id: UUID) -> dict[str, Any] | None:
        """Retrieve full chronological timeline of a round (cards, decisions, bankroll ledger)."""
        ...

    async def get_player_benchmark_summary(self, simulation_id: UUID) -> list[dict[str, Any]]:
        """Compute win rate, ROI, total wagers, and basic strategy agreement % per player."""
        ...
```

---

## 4. Run Archival Exporter Contract

`backend/app/persistence/exporter.py`

```python
from pathlib import Path
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

class RunExporter:
    """Exports a completed Run to structured file records."""

    def __init__(self, session: AsyncSession, base_dir: Path | str = "/app/data/runs") -> None:
        self.session = session
        self.base_dir = Path(base_dir)

    async def export_run_to_json(self, run_id: UUID) -> Path:
        """Serialize run, configurations, simulations, rounds, and metrics to JSON artifact.
        
        Returns:
            Path to the written run_data.json artifact.
        """
        ...
```
