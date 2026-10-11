# Implementation Plan: Database Schema & Simulation Telemetry Persistence

**Branch**: `004-database-persistence` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)

**Input**: User description: "Let's create the database for the project. You may take a look at docs/Diseño Base de Datos (Modelo ER).md to get an idea of what the database should have. Use the dedicated docker container for the db. A postgreSQL image is used inside the container. Use sqlalchemy as the orm"

---

## Summary

Implement the complete relational persistence layer for Decision_Blackjack based on [`docs/Diseño Base de Datos (Modelo ER).md`](../../docs/Diseño%20Base%20de%20Datos%20(Modelo%20ER).md) using SQLAlchemy 2.0 AsyncIO with the dedicated PostgreSQL 16 Docker container (`app_db`). The layer provides:
1. Strongly-typed ORM mapping for all 15 domain entities across 6 functional domains with UUID keys, PostgreSQL ENUMs, composite uniqueness, and cascading foreign keys.
2. A decoupled, asynchronous `SimulationPersistenceListener` that subscribes to orchestrator events via `EventEmitter` and commits data in atomic round-boundary transactions.
3. A `RunRepository` providing analytical queries, round replay timelines, model benchmarks, and cascading deletions.
4. A `RunExporter` generating structured JSON run archives at `/data/runs/[timestamp]/run_data.json`.

---

## Technical Context

**Language/Version**: Python 3.12+ (managed with `uv`)

**Primary Dependencies**: SQLAlchemy 2.0+ (`sqlalchemy.ext.asyncio`), asyncpg 0.29+, FastAPI 0.115+, Pydantic 2.9+

**Storage**: PostgreSQL 16 (running in dedicated Docker container `app_db`, `postgres:16-alpine`, exposed on port 5432)

**Testing**: Python unittest / pytest suite (`backend/tests/test_persistence_*.py`), with graceful test skipping when the PostgreSQL Docker container is unreachable

**Target Platform**: Linux (Docker container `app_backend`), macOS local development

**Project Type**: Web service & backend simulation persistence package (`backend/app/persistence`)

**Performance Goals**:
- Event ingestion overhead $< 15\text{ ms}$ per round event
- Full 3-player round replay timeline query $< 50\text{ ms}$
- High-volume batch write latency $< 200\text{ ms}$ per batch
- Process RAM growth $< 256\text{ MB}$ over 10,000 simulation rounds

**Constraints**:
- Strict engine independence (Constitution Principle I & V): zero game rule execution or validation inside database or SQL queries
- Asynchronous non-blocking I/O across all database calls
- Atomic round-boundary transactions: intermediate events committed at round completion or every $N$ completed rounds
- 100% cascade deletion across descendant foreign keys (`ON DELETE CASCADE`)

**Scale/Scope**: 15 relational entities, up to 10,000+ simulation rounds per run

---

## Constitution Check

*GATE: All principles pass cleanly.*

| Principle | Status | Evaluation |
|---|:---:|---|
| **I. Engine Independence & Determinism** | **PASS** | The blackjack engine executes in-memory with zero knowledge of PostgreSQL or SQL. The database serves strictly as an asynchronous telemetry recorder and query repository. |
| **II. Tri-Entity Synchronization & Experiment Isolation** | **PASS** | Schema models independent `PLAYER_SESSION`, `ROUND_PLAYER`, and `PLAYER_SHOE_STATE` records for Jev, Laya, and Optimal while sharing identical run configuration and initial shoe sequence. |
| **III. Provider Abstraction & Model Decoupling** | **PASS** | `MODEL_RESPONSE` persists raw AI provider payloads, latencies, and error codes without coupling engine models to external vendor protocols. Sensitive API keys are never stored in DB or exported JSON. |
| **IV. Seeded Reproducibility** | **PASS** | `RUN_CONFIGURATION.user_seed`, `SIMULATION.seed`, `SHOE.seed`, and `SHOE.card_order` record deterministic PRNG states for auditability. |
| **V. Telemetry, Structured Persistence & Batch Safety** | **PASS** | PostgreSQL schema captures every card deal, decision, model latency, and bankroll transaction. Round-boundary batch flushing guarantees memory stability on large runs ($>10,000$ rounds). `RunExporter` archives to `/data/runs/[timestamp]`. |
| **Technology Stack & Architectural Constraints** | **PASS** | Uses PostgreSQL in Docker Compose (`app_db`), SQLAlchemy 2.0 AsyncIO, asyncpg, and FastAPI integration. |
| **Development Workflow & Quality Gates** | **PASS** | Automated tests cover schema creation, event ingestion, queries, and exports. Tests skip cleanly if DB is offline. |

---

## Project Structure

### Documentation (this feature)

```text
specs/004-database-persistence/
├── spec.md                  # Feature specification
├── plan.md                  # This implementation plan
├── research.md              # Technical research & architectural decisions
├── data-model.md            # 15-entity relational data model & SQL definitions
├── contracts/
│   └── persistence_service.md # Public API contracts for database, listener, repository, exporter
├── quickstart.md            # End-to-end runnable validation scenarios
├── checklists/
│   └── requirements.md      # Specification quality checklist (16/16 pass)
└── tasks.md                 # Implementation task breakdown (created by /speckit-tasks)
```

### Source Code Layout

```text
backend/
├── app/
│   └── persistence/
│       ├── __init__.py           # Public exports (models, database, repositories, listener)
│       ├── database.py           # Async engine, sessionmaker, init_db, health check
│       ├── models.py             # 15 SQLAlchemy 2.0 async ORM models & PostgreSQL ENUMs
│       ├── listener.py           # SimulationPersistenceListener subscribing to EventEmitter
│       ├── repositories.py       # RunRepository (queries, replays, benchmarks, cascade delete)
│       ├── exporter.py           # RunExporter (/data/runs/[timestamp]/run_data.json)
│       └── migrations/
│           └── init_schema.sql   # Standalone DDL script for production/docker deployment
│
├── tests/
│   ├── test_persistence_schema.py       # Entity modeling, table creation, constraints, cascades
│   ├── test_persistence_listener.py     # Event ingestion and round-boundary batch flushing
│   ├── test_persistence_repository.py   # Historical queries, round replay, benchmarks
│   ├── test_persistence_exporter.py     # JSON export generation and structure validation
│   └── test_persistence_quickstart.py   # End-to-end quickstart validation scenarios
│
└── docker-compose.yml                    # Existing postgres:16-alpine service (app_db)
```

**Structure Decision**: Package all persistence logic in `backend/app/persistence/` adhering to the existing modular backend pattern (`engine`, `simulation`, `models`, `persistence`, `api`).

---

## Complexity Tracking

*No constitution violations or unjustified architectural complexities detected.*
