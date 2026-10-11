# Tasks: Database Schema & Simulation Telemetry Persistence

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Package**: `backend/app/persistence/`  
**Date**: 2026-10-11  

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize package structure, public exports, and async database engine configuration.

- [x] T001 Initialize package structure in `backend/app/persistence/` with public export declarations in `backend/app/persistence/__init__.py`
- [x] T002 [P] Implement async PostgreSQL database connection engine, sessionmaker, health check, and connection pooling in `backend/app/persistence/database.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core ORM base definitions, PostgreSQL ENUMs, and DDL schema migration that MUST be completed before implementing user stories.

**⚠️ CRITICAL**: All domain entities and schema definitions depend on these foundational components.

- [x] T003 [P] Define all 18 PostgreSQL ENUM types (`run_status`, `simulation_status`, `player_type`, `session_status`, `termination_reason`, `round_status`, `player_round_status`, `hand_status`, `card_recipient`, `card_event_type`, `decision_type`, `player_action`, `model_provider`, `bet_type`, `hand_result_type`, `transaction_type`, `soft_17_rule`, `hole_card_rule`, `split_aces_blackjack_rule`, `surrender_rule`, `charlie_rule`) and `Base = DeclarativeBase()` in `backend/app/persistence/models.py`
- [x] T004 [P] Implement complete declarative DDL schema migration script with all 15 tables, ENUMs, foreign keys with `ON DELETE CASCADE`, unique constraints, and indexes in `backend/app/persistence/migrations/init_schema.sql`

**Checkpoint**: Foundation ready — database connection, base classes, ENUMs, and migration scripts exist.

---

## Phase 3: User Story 1 - Relational Database Schema & Domain Entity Integrity (Priority: P1) 🎯 MVP

**Goal**: Deliver the complete 15-entity relational schema mapped across 6 functional domains in `backend/app/persistence/models.py` with UUID keys, composite uniqueness, and cascade deletes.

**Independent Test**: Can be tested independently by running schema initialization against PostgreSQL, verifying all 15 tables and indexes are created, constraints block invalid inserts, and tests skip cleanly if PostgreSQL is unreachable.

### Tests for User Story 1 ⚠️

- [x] T005 [P] [US1] Create unit tests in `backend/tests/test_persistence_schema.py` verifying table creation, composite unique constraints (`UNIQUE (simulation_id, player_type)`, `UNIQUE (round_id, player_session_id)`), check constraints, cascade deletes, and graceful test skipping if PostgreSQL is unreachable

### Implementation for User Story 1

- [x] T006 [US1] Implement Execution and Participant domain ORM models (`Run`, `RunConfiguration`, `Simulation`, `PlayerSession`) with UUID primary keys, composite uniqueness `UNIQUE (run_id, simulation_number)` and `UNIQUE (simulation_id, player_type)`, and `ON DELETE CASCADE` in `backend/app/persistence/models.py`
- [x] T007 [US1] Implement Shoes and Game Flow domain ORM models (`Shoe`, `PlayerShoeState`, `Round`, `RoundPlayer`, `Hand`, `CardEvent`) with `parent_hand_id` tree hierarchy, `UNIQUE (player_session_id, shoe_id)`, and `UNIQUE (simulation_id, round_number)` in `backend/app/persistence/models.py`
- [x] T008 [US1] Implement Decisions, AI, and Economy domain ORM models (`Decision`, `ModelResponse`, `Bet`, `HandResult`, `BankrollTransaction`) with `optimal_reference_action`, `agrees_with_optimal`, and `balance_after == balance_before + amount` invariant in `backend/app/persistence/models.py`
- [x] T009 [US1] Implement `init_db(engine)` in `backend/app/persistence/database.py` utilizing `Base.metadata.create_all` to auto-provision all 15 tables and indexes on test and service startup

**Checkpoint**: User Story 1 is functional! All 15 entities, relationships, constraints, and indexes are mapped and auto-provisionable.

---

## Phase 4: User Story 2 - Real-Time Orchestrator Event Ingestion & Audit Logging (Priority: P1)

**Goal**: Implement the asynchronous `SimulationPersistenceListener` that subscribes to orchestrator events and persists card events, decisions, model responses, bets, and ledger transactions.

**Independent Test**: Can be tested independently by dispatching synthetic orchestrator events through `EventEmitter` to the listener and asserting that records are properly written to PostgreSQL with valid foreign key linkages.

### Tests for User Story 2 ⚠️

- [x] T010 [P] [US2] Create integration tests in `backend/tests/test_persistence_listener.py` verifying event subscription, entity translation, `optimal_reference_action` capture, `MODEL_RESPONSE` payload persistence, and atomic round commits

### Implementation for User Story 2

- [x] T011 [US2] Implement `SimulationPersistenceListener` class with `attach()`, `detach()`, and event routing methods subscribing to orchestrator `EventEmitter` in `backend/app/persistence/listener.py`
- [x] T012 [US2] Implement turn and decision event mapping in `backend/app/persistence/listener.py` persisting `Decision` (with `optimal_reference_action` and `agrees_with_optimal`), `ModelResponse` (payloads, latency, status), and sequential `CardEvent` records
- [x] T013 [US2] Implement round lifecycle and ledger mapping in `backend/app/persistence/listener.py` recording `Bet`, `RoundPlayer` bankroll balances, `HandResult`, and signed `BankrollTransaction` records

**Checkpoint**: User Story 2 is functional! The orchestrator event stream writes directly to the database asynchronously.

---

## Phase 5: User Story 3 - High-Volume Batch Persistence & Structured Run Export (Priority: P2)

**Goal**: Implement atomic round-boundary batch flushing for high-speed runs ($>10,000$ rounds) and file export of complete runs to `/data/runs/[timestamp]/run_data.json`.

**Independent Test**: Can be tested independently by buffering batches of rounds, verifying atomic transaction commits, and asserting that `RunExporter` writes a valid self-contained JSON artifact matching the run hierarchy.

### Tests for User Story 3 ⚠️

- [x] T014 [P] [US3] Create integration tests in `backend/tests/test_persistence_exporter.py` verifying atomic round-boundary batch flushing, error status persistence on pause/abort, and structured JSON export generation

### Implementation for User Story 3

- [x] T015 [US3] Implement atomic round-boundary buffering and configurable batch flush logic ($N$ rounds) with error-state recovery (`RUN.status = 'ERROR'`) in `backend/app/persistence/listener.py`
- [x] T016 [US3] Implement `RunExporter` in `backend/app/persistence/exporter.py` serializing complete runs into `/data/runs/[timestamp]/run_data.json` matching the 15-entity hierarchy

**Checkpoint**: User Story 3 is functional! Batch persistence safeguards large runs and runs are exportable to structured JSON.

---

## Phase 6: User Story 4 - Historical Simulation Querying & Analytical Replay (Priority: P2)

**Goal**: Implement `RunRepository` providing query interfaces for run summaries, chronological round replay timelines, model benchmark comparisons, and cascading run deletions.

**Independent Test**: Can be tested independently by querying a persisted run, verifying that chronological round timelines and dynamically computed win rates and agreement percentages match raw game events.

### Tests for User Story 4 ⚠️

- [x] T017 [P] [US4] Create query tests in `backend/tests/test_persistence_repository.py` verifying run creation, listing, round replay timeline retrieval, dynamic benchmark metrics calculation, and hard cascade deletion

### Implementation for User Story 4

- [x] T018 [US4] Implement `RunRepository.create_run`, `get_run`, `list_runs`, and `delete_run` with complete cascading deletion in `backend/app/persistence/repositories.py`
- [x] T019 [US4] Implement `RunRepository.get_round_replay` in `backend/app/persistence/repositories.py` retrieving ordered cards, decisions, state snapshots, and ledger transactions by `sequence_number`
- [x] T020 [US4] Implement `RunRepository.get_player_benchmark_summary` in `backend/app/persistence/repositories.py` dynamically computing win rates, ROI, total bets, and basic strategy agreement percentage without storing stale columns

**Checkpoint**: User Story 4 is functional! Replay timelines and comparative model benchmarks are fully queryable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate quickstart scenarios, run static analysis and linting, and update project documentation.

- [x] T021 [P] Validate all scenarios from `specs/004-database-persistence/quickstart.md` in `backend/tests/test_persistence_quickstart.py`
- [x] T022 [P] Run static analysis and formatting checks via `ruff check backend/app/persistence backend/tests`
- [x] T023 Execute complete project test suite verifying 100% test pass rate across engine, simulation, models, and persistence via `python3` test runners
- [x] T024 Update `docs/session_logs.md` documenting persistence layer architecture, database models, and API reference

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can begin immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001–T002) - BLOCKS all User Stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion (T003–T004). Delivers MVP.
- **User Story 2 (Phase 4)**: Depends on US1 completion (T006–T009).
- **User Story 3 (Phase 5)**: Depends on US2 completion (T011–T013).
- **User Story 4 (Phase 6)**: Depends on US1 & US2 completion (T006–T009, T011–T013).
- **Polish (Phase 7)**: Depends on all user stories being completed.

### Parallel Opportunities

- **Phase 1**: T001 (`__init__.py`) and T002 (`database.py`) can run in parallel.
- **Phase 2**: T003 (`models.py` ENUMs/Base) and T004 (`init_schema.sql`) can run in parallel.
- **Phase 3**: T005 (Schema tests) can be written in parallel with T006.
- **Phase 4**: T010 (Listener tests) can be written in parallel with T011.
- **Phase 5**: T014 (Exporter tests) can be written in parallel with T015.
- **Phase 6**: T017 (Repository tests) can be written in parallel with T018.
- **Phase 7**: T021 (`test_persistence_quickstart.py`) and T022 (`ruff check`) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 (Setup: package structure and async connection engine).
2. Complete Phase 2 (Foundational: ENUM types, base classes, and DDL script).
3. Complete Phase 3 (User Story 1: 15 ORM models, constraints, auto-provisioning).
4. **STOP and VALIDATE**: Verify that tables auto-provision and all constraints/cascades pass.

### Incremental Delivery
1. Add Phase 4 (User Story 2: Asynchronous event ingestion listener).
2. Add Phase 5 (User Story 3: Atomic batch flushing and `/data/runs` JSON export).
3. Add Phase 6 (User Story 4: Historical queries, replay timelines, benchmarks, cascade delete).
4. Run Phase 7 (Polish: quickstart tests, linting, regression verification).
