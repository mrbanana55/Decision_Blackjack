# Technical Research: Database Schema & Telemetry Persistence

**Feature**: `specs/004-database-persistence` | **Date**: 2026-10-11

---

## 1. ORM Architecture & Async Database Driver

### Decision
Use **SQLAlchemy 2.0+ with AsyncIO (`sqlalchemy.ext.asyncio`)** paired with **`asyncpg`** as the PostgreSQL driver. All models inherit from a declarative `Base = DeclarativeBase()`, using typed `Mapped[...]` and `mapped_column(...)` annotations.

### Rationale
- **Native AsyncIO Support**: FastAPI and the simulation orchestrator run in Python's async event loop. `asyncpg` is the fastest asynchronous PostgreSQL driver in Python, preventing event-loop stalls.
- **SQLAlchemy 2.0 Typed API**: Provides full type safety, modern query semantics (`select()`, `insert()`), robust relationship definitions, and clean JSONB / UUID / Enum column types.
- **Project Pre-Alignment**: `backend/pyproject.toml` already specifies `sqlalchemy[asyncio]>=2.0.35` and `asyncpg>=0.29.0`, and `docker-compose.yml` configures `DATABASE_URL: postgresql+asyncpg://...`.

### Alternatives Considered
- *SQLAlchemy Core only*: Lacks ergonomic entity relationships and cascade handling; writing raw SQL or table clauses for 15 complex relational models is error-prone.
- *Tortoise-ORM / Peewee*: Less mature type checking, smaller ecosystem, and lacks deep PostgreSQL-native JSONB/cascade control compared to SQLAlchemy 2.0.
- *Psycopg3 async*: Modern and capable, but SQLAlchemy with asyncpg provides the ORM mapping and unit-of-work abstractions requested by the user.

---

## 2. Dockerized PostgreSQL Container & Connection Management

### Decision
Use the dedicated PostgreSQL container configured in `docker-compose.yml` (`image: postgres:16-alpine`, service name `db`, container `app_db`). Connection management uses `create_async_engine` with a pooled connection (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`) and an `async_sessionmaker` for scoped sessions.

### Rationale
- **User Constraint**: The user explicitly instructed: *"Use the dedicated docker container for the db. A postgreSQL image is used inside the container. Use sqlalchemy as the orm"*.
- **PostgreSQL 16 Features**: Excellent JSONB indexing, robust connection handling, and lightweight footprint on Alpine Linux.
- **Connection Pooling**: `pool_pre_ping=True` ensures stale connections across idle periods or container restarts are transparently recycled without application crashes.

### Alternatives Considered
- *Single-connection / unpooled engine*: Exhausts database sockets during high-speed multi-agent simulations.
- *Embedded / local host postgres*: Fragile across developer machines; Docker container guarantees identical database versions and extensions.

---

## 3. Schema Provisioning & Migration Strategy

### Decision
Implement **hybrid schema provisioning**:
1. An async `init_db(engine)` function executing `Base.metadata.create_all` for fast startup and test provisioning.
2. A declarative DDL migration script (`backend/app/persistence/migrations/init_schema.sql` or standalone Python migration runner) that can be executed independently against live databases or CI environments.
3. Database tests inspect connectivity to `DATABASE_URL`; if PostgreSQL is unavailable, database-dependent integration tests skip cleanly with a clear notice (`pytest.mark.skipif`).

### Rationale
- Directly implements Clarification Q2 (Option A: Auto-provision with migration scripts) and Clarification Q4 (Option B: Strict PostgreSQL dependency with test skipping).
- Prevents boilerplate migration friction during initial development while maintaining production-ready DDL scripts.

### Alternatives Considered
- *Strict Alembic migrations only*: Adds migration generation overhead for the initial Greenfield schema creation. Alembic can be layered on in future iterations for incremental schema changes.
- *In-memory SQLite for tests*: Rejected by user clarification (Q4 chose Option B: strict PostgreSQL dependency to preserve native JSONB, UUID, and Enum constraints).

---

## 4. Telemetry Event Ingestion & Batch Flushing Policy

### Decision
Implement an asynchronous `SimulationPersistenceListener` that subscribes to the orchestrator's `EventEmitter` (listening to `SHOE_GENERATED`, `CARD_DEALT`, `DECISION_APPLIED`, `ROUND_STARTED`, `ROUND_COMPLETED`, `SIMULATION_COMPLETED`).
- **Standard Mode**: Intermediate turn and card events are accumulated in an in-memory round buffer and committed in an atomic database transaction upon `ROUND_COMPLETED`.
- **High-Volume Mode ($>10,000$ rounds)**: Events are buffered across rounds and flushed in batches of $N$ rounds (configurable, default 50 rounds) or when a buffer flush timeout elapses.
- **Failure Recovery**: If a simulation pauses with an error, the listener commits the active partial round with error metadata and marks `RUN.status = 'ERROR'`.

### Rationale
- Directly implements Clarification Q1 (Option A: Asynchronous event subscriber via `EventEmitter`) and Clarification Q3 (Option A: Atomic round-boundary batch flush).
- Engine independence (Constitution Principle I): The orchestrator loop never blocks waiting for database I/O, maintaining the <15 ms event processing budget.

### Alternatives Considered
- *Synchronous inline inserts in EntityTable*: Violates Constitution Principle I by intertwining database network I/O with core blackjack game loop logic.
- *Global background thread with shared memory*: Adds multithreading locking complexity; Python asyncio queue / event listener is cleaner and native to FastAPI.

---

## 5. Structured Run Archival & Export Format

### Decision
Implement `RunExporter` in `backend/app/persistence/exporter.py` that serializes completed runs into `/data/runs/[timestamp]/run_data.json` matching the 15-entity relational schema hierarchy:
`Run` $\rightarrow$ `RunConfiguration`, `Simulations` $\rightarrow$ `PlayerSessions`, `Shoes`, `Rounds` (with `RoundPlayers`, `Hands`, `CardEvents`, `Decisions`, `Bets`, `LedgerTransactions`).

### Rationale
- Fulfills Constitution Principle V: Structured file export at `/data/runs/[timestamp]` for external statistical evaluation and headless auditability.
- Decouples downstream analytical tools from live database queries.

### Alternatives Considered
- *CSV / Flat files*: Cannot represent the recursive hand tree (`parent_hand_id`) or raw AI model payloads (`MODEL_RESPONSE.request_payload`) without loss of structure.
- *Parquet*: Good for columnar data, but JSON is more readable, standard across frontend/web inspection, and directly supported by Python standard library without heavy dependencies.

---

## 6. Cascade Deletion Strategy

### Decision
Define explicit `ondelete="CASCADE"` on all foreign key constraints and `cascade="all, delete-orphan"` on all parent SQLAlchemy relationship definitions starting from `Run.simulations` down to child tables.

### Rationale
- Directly satisfies Clarification Q5 (Option A: Hard cascading deletion).
- Guarantees zero dangling records across child tables when testing, developing, or purging runs.

### Alternatives Considered
- *Soft-delete only*: Rejected during clarification Q5. Leaves large disk footprints in benchmarking environments where millions of simulated card events are generated.
