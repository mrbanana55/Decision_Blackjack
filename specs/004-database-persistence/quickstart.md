# Quickstart: Database Schema & Telemetry Persistence

**Feature**: `specs/004-database-persistence` | **Date**: 2026-10-11

This guide provides end-to-end walkthroughs to validate the database schema, orchestrator event ingestion, analytical queries, and file archival export against the dedicated PostgreSQL Docker container.

---

## 1. Prerequisites & Environment Setup

Start the PostgreSQL service using Docker Compose:

```bash
# 1. Start the database container
docker compose up -d db

# 2. Verify container health
docker compose ps db
# Output should show: app_db ... (healthy)
```

Ensure environment configuration in `.env` (or default):
```bash
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/decision_blackjack"
```

---

## 2. Validation Scenarios

### Scenario 1: Schema Auto-Provisioning & Entity Integrity

Verify that running `init_db()` creates all 15 relational tables, enumerations, and foreign key cascades without errors.

```python
import asyncio
from backend.app.persistence.database import get_engine, init_db, check_db_health
from backend.app.persistence.models import Base

async def test_schema_provisioning():
    engine = get_engine()
    assert await check_db_health(engine), "Database container is unreachable!"
    
    # Auto-provision tables
    await init_db(engine)
    print("✓ Schema initialized successfully across all 15 domain entities.")

asyncio.run(test_schema_provisioning())
```

---

### Scenario 2: Real-Time Event Ingestion from Simulation Run

Attach the `SimulationPersistenceListener` to the orchestrator's `EventEmitter`, execute a 3-player round, and verify records in PostgreSQL.

```python
import asyncio
from backend.app.persistence.database import get_session_factory
from backend.app.persistence.repositories import RunRepository
from backend.app.persistence.listener import SimulationPersistenceListener
from backend.app.simulation.orchestrator import SimulationOrchestrator
from backend.app.simulation.types import OrchestratorConfig, EntityType

async def test_event_ingestion():
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        repo = RunRepository(session)
        # 1. Create Run in DB
        run = await repo.create_run({
            "soft_17_rule": "STAND",
            "blackjack_payout_ratio": 1.5,
            "number_of_decks": 6,
            "initial_bankroll": 1000.0,
            "minimum_bet": 25.0,
            "maximum_bet": 500.0,
            "rounds_per_simulation": 5,
        })
        run_id = run.id

    # 2. Configure orchestrator and attach persistence listener
    config = OrchestratorConfig(
        entities=[EntityType.OPTIMAL, EntityType.JEV, EntityType.LAYA],
        max_rounds=1,
        seed=42,
    )
    orchestrator = SimulationOrchestrator(config)
    listener = SimulationPersistenceListener(run_id=run_id, event_emitter=orchestrator.events)
    listener.attach()

    # 3. Run round
    await orchestrator.start()
    await listener.flush()
    listener.detach()

    # 4. Verify persisted state
    async with session_factory() as session:
        repo = RunRepository(session)
        run_record = await repo.get_run(run_id)
        assert run_record is not None
        assert len(run_record.simulations) > 0
        print(f"✓ Event ingestion verified: Run {run_id} persisted with rounds and decisions.")

asyncio.run(test_event_ingestion())
```

---

### Scenario 3: Historical Round Replay & Analytical Metrics

Retrieve the chronological timeline of a completed round and compute comparative performance metrics without calculating derived columns manually.

```python
import asyncio
from backend.app.persistence.database import get_session_factory
from backend.app.persistence.repositories import RunRepository

async def test_round_replay_and_metrics(run_id):
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = RunRepository(session)
        run = await repo.get_run(run_id)
        sim_id = run.simulations[0].id

        # 1. Benchmark metrics summary
        summary = await repo.get_player_benchmark_summary(sim_id)
        for player_stat in summary:
            print(f"Player: {player_stat['player_type']} | Bankroll: ${player_stat['current_bankroll']} | "
                  f"Optimal Agreement: {player_stat['agreement_pct']:.1f}%")

        # 2. Full chronological round replay
        round_id = run.simulations[0].rounds[0].id
        replay = await repo.get_round_replay(round_id)
        print(f"✓ Replay loaded: {len(replay['card_events'])} cards dealt, {len(replay['decisions'])} decisions.")

asyncio.run(test_round_replay_and_metrics(run_id))
```

---

### Scenario 4: Structured Run Archival Export

Export the complete run hierarchy to `/data/runs/[timestamp]/run_data.json`.

```python
import asyncio
from backend.app.persistence.database import get_session_factory
from backend.app.persistence.exporter import RunExporter

async def test_run_export(run_id):
    session_factory = get_session_factory()
    async with session_factory() as session:
        exporter = RunExporter(session, base_dir="./data/runs")
        export_file = await exporter.export_run_to_json(run_id)
        assert export_file.exists(), "Export file was not created!"
        print(f"✓ Run successfully exported to: {export_file}")

asyncio.run(test_run_export(run_id))
```

---

### Scenario 5: Cascading Run Deletion

Verify that deleting a `RUN` cleanly cascades through foreign keys to delete all associated simulations, rounds, card events, and ledger records.

```python
import asyncio
from backend.app.persistence.database import get_session_factory
from backend.app.persistence.repositories import RunRepository

async def test_cascade_delete(run_id):
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = RunRepository(session)
        deleted = await repo.delete_run(run_id)
        assert deleted is True
        
        # Verify run and children are gone
        assert await repo.get_run(run_id) is None
        print(f"✓ Cascade deletion verified: Run {run_id} and all child records purged.")

asyncio.run(test_cascade_delete(run_id))
```

---

## 3. Running Automated Tests

Run the persistence test suite:

```bash
# Execute persistence tests (requires running PostgreSQL container)
PYTHONPATH=backend python3 -m pytest backend/tests/test_persistence_*.py -v
```
