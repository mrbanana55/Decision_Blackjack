# Engineering Session Logs

This document tracks daily engineering milestones, architectural decisions, and deliverables across the Decision Blackjack project.

---

## Session: 2026-10-09

**Focus**: Core Blackjack Engine Specification, Architecture, Implementation, and Verification  
**Branch**: `main` (Feature directory: `specs/001-core-blackjack-engine/`)  
**Status**: Completed & Verified (100% Test Pass Rate, 35/35 tests)

---

### 1. Executive Summary

Today's session was dedicated to building the complete **Core Deterministic Blackjack Engine** from scratch. Following the Spec-Kit methodology (`specify` → `clarify` → `plan` → `tasks` → `implement`), we designed and implemented a pure in-memory, deterministic finite-state-machine (FSM) residing in `backend/app/engine/`. 

The engine has **zero external UI, database, or HTTP dependencies**, making it highly performant (0.0416 ms per round) and capable of running both headless simulations and external test controller scenarios without any mock or hardcoded test hands in production code.

---

### 2. Specification & Key Clarifications Resolved

During the `/speckit-specify` and `/speckit-clarify` stages, 5 critical domain decisions were formalized:

1. **Card Injection for Tests (`FR-012`)**: The `Shoe` accepts an optional FIFO `card_sequence` list that external controllers can supply for predictable test hands before falling back to seeded pseudo-random shuffling. Zero test hands are hardcoded in the engine.
2. **Sequential Split Dealing (`FR-006`)**: When a player splits, Hand 1 receives its second card immediately and is played to completion (stood, doubled, or busted) before Hand 2 receives its second card and becomes active.
3. **Immediate Bankroll Accounting (`FR-001`, `FR-009`)**: Stakes for opening bets, double downs, split hands, and insurance are deducted immediately upon action commitment; winnings, bonus payouts, and returned stakes are credited at round settlement.
4. **European No Hole Card (ENHC) Loss Rule (`FR-007`)**: Total Bets Lost (TBL) was adopted. If the player doubles or splits and the dealer later achieves a Natural Blackjack, all staked wagers are forfeited.
5. **Cut-Card Penetration Handling (`FR-008`)**: When the penetration threshold is reached mid-round, the current round finishes with the active shoe; a full reshuffle is triggered automatically before dealing the subsequent round.

---

### 3. Architecture & Implemented Components

The engine is modularized across 9 clean files in `backend/app/engine/`:

| Module | Core Responsibility |
| :--- | :--- |
| [`types.py`](../backend/app/engine/types.py) | Canonical domain enums (`Action`, `RoundPhase`, `HandStatus`, `Soft17Rule`, `DealerStyle`, `SurrenderRule`, `SettlementOutcome`) with case-insensitive string equality. |
| [`interfaces.py`](../backend/app/engine/interfaces.py) | Protocols (`RoundController`, `CardSource`, `RoundEventListener`) and domain exceptions (`EngineError`, `IllegalActionError`, `InvalidStateError`, `InvalidBetError`, `InsufficientFundsError`, `ShoeEmptyError`). |
| [`card.py`](../backend/app/engine/card.py) | Immutable `Card` primitive (`Suit`, `Rank`, nominal value, `is_ace`, unicode card rendering). |
| [`hand.py`](../backend/app/engine/hand.py) | `Hand`, `PlayerHand`, and `DealerHand` with dynamic Ace softness reduction ($11 \rightarrow 1$), bust detection, and natural Blackjack vs split 21 distinction. |
| [`shoe.py`](../backend/app/engine/shoe.py) | Multi-deck card shoe (1–8 decks), deterministic PRNG seed, burn cards, cut-card index tracking, mid-round discard recovery, and FIFO injection. |
| [`rules.py`](../backend/app/engine/rules.py) | `TableRules` configuration model (S17/H17, payout ratios, American Peek vs ENHC, DAS, RSA, table boundaries). |
| [`settlement.py`](../backend/app/engine/settlement.py) | Pure settlement resolution (`settle_round`, `HandSettlement`, `RoundSettlement`) computing gross returns, net PnL, and final bankroll. |
| [`round.py`](../backend/app/engine/round.py) | Core finite state machine (`BlackjackRound` & `RoundState` snapshot) orchestrating the complete round lifecycle from initial bet to settlement. |
| [`__init__.py`](../backend/app/engine/__init__.py) | Package public API exports. |

---

### 4. Verification & Testing

All 31 tasks (T001–T031) defined in [`tasks.md`](../specs/001-core-blackjack-engine/tasks.md) were executed and verified against a 35-test automated test suite across 6 test modules:

- **[`test_engine_card_hand.py`](../backend/tests/test_engine_card_hand.py)** (7 tests): Card properties, hard/soft totals, Ace reduction, bust checks, natural BJ vs split 21, dealer hole card concealing.
- **[`test_engine_shoe.py`](../backend/tests/test_engine_shoe.py)** (6 tests): Sizing, determinism across identical seeds, penetration flags, FIFO dealing, discard tray recovery, between-round reshuffle.
- **[`test_engine_round.py`](../backend/tests/test_engine_round.py)** (7 tests): Round lifecycle, immediate bankroll deductions, hit/stand transitions, dealer drawing/busting, direct natural BJ payouts, push refunds, bet boundaries.
- **[`test_engine_rules.py`](../backend/tests/test_engine_rules.py)** (6 tests): Dealer stands on S17 vs hits on H17, payout ratios (3:2, 6:5, 1:1), American Peek immediate termination, ENHC TBL on double down, illegal action rejections.
- **[`test_engine_splits_sidebets.py`](../backend/tests/test_engine_splits_sidebets.py)** (7 tests): Sequential split dealing, split Aces auto-stand when `hit_split_aces=False`, split 21 standard payout, double down wagers, DAS restrictions, insurance 2:1 payouts, surrender 50% refunds.
- **[`test_quickstart.py`](../backend/tests/test_quickstart.py)** (2 tests): End-to-end verification of scenarios from [`quickstart.md`](../specs/001-core-blackjack-engine/quickstart.md).

```text
=== Test Execution Summary ===
tests.test_engine_card_hand        : 7 passed
tests.test_engine_shoe             : 6 passed
tests.test_engine_round            : 7 passed
tests.test_engine_rules            : 6 passed
tests.test_engine_splits_sidebets  : 7 passed
tests.test_quickstart              : 2 passed
----------------------------------------
Total: 35 passed, 0 failed (100% Pass Rate)
```

---

### 5. Performance Benchmarks (`SC-001` & `SC-004`)

An automated headless benchmark playing 1,000 complete rounds was executed:
- **Total Duration**: 0.0416 seconds for 1,000 rounds.
- **Average Round Speed**: **0.0416 ms / round** (48x faster than the 2.0 ms target in `SC-004`).

---

### 6. Interactive Player Experience

Created [`play.py`](../play.py) in the project root:
- An interactive terminal game featuring colored suit emojis (`[A♠]`, `[10♥]`), real-time bankroll tracking, legal actions prompt (`h/s/d/p/r`), insurance offers, sequential split handling, and dealer resolution.
- Playable immediately via:
  ```bash
  python3 play.py
  ```

---

### 7. Documentation Delivered

- [`docs/Blackjack_Engine.md`](Blackjack_Engine.md): Comprehensive architecture guide and API reference.
- [`docs/session_logs.md`](session_logs.md): This log entry.
- [`specs/001-core-blackjack-engine/`](../specs/001-core-blackjack-engine/): Full Spec-Kit artifacts (`spec.md`, `plan.md`, `tasks.md`, `data-model.md`, `quickstart.md`, `research.md`, `checklists/requirements.md`).

---

## Session: 2026-10-10

**Focus**: Simulation Orchestrator Specification, Architecture, Multi-Agent Flow Control, Generational Shoe Lifecycle, and Verification  
**Branch**: `main` (Feature directory: `specs/002-simulation-orchestrator/`)  
**Status**: Completed & Verified (100% Test Pass Rate, 41/41 simulation tests, 76/76 total tests across codebase)

---

### 1. Executive Summary

Today's session focused on designing and implementing the **Simulation Orchestrator** in `backend/app/simulation/`. Following the complete Spec-Kit lifecycle (`specify` → `clarify` → `plan` → `tasks` → `implement`), we built an asynchronous, in-memory, headless multi-agent benchmarking coordinator.

The orchestrator enables reproducible comparisons across multiple decision entities (Jev, Laya, and Optimal Basic Strategy) playing isolated table instances under identical initial conditions. Crucially, it manages asynchronous concurrent execution using a synchronous round barrier, provides non-blocking operational flow controls (`pause`, `resume`, `step_round`, `step_turn`, `stop`), enforces fail-fast error handling with synchronous recovery, administrates a generational shoe pool across desynchronized table depletion rates, and broadcasts strongly typed domain events for telemetry and persistence.

All agents are isolated behind the `DecisionProvider` protocol, and fake test agents (`FakeJevAgent`, `FakeLayaAgent`) reside in `backend/app/simulation/agents/fake_agents.py`, allowing them to be swapped cleanly for real model integrations in future specifications without altering the orchestrator core.

---

### 2. Specification & Key Clarifications Resolved

During the `/speckit-specify` and user feedback refinement cycle, 4 core architectural decisions were established:

1. **Concurrent Execution with Round Barrier (`FR-004`, `FR-005`)**: Active entity tables execute their decision turns concurrently using `asyncio.gather`. All tables must complete and settle round $N$ before the orchestrator initiates round $N+1$.
2. **Fail-Fast Fault Recovery (`FR-009`, `FR-010`)**: When any agent provider experiences a timeout, unhandled exception, or illegal action, all tables halt immediately in `PAUSED_ERROR` state, preserving all in-flight table and shoe states. The controller can inspect telemetry and invoke `retry_failed_entity(entity_id)` to resume cleanly.
3. **Generational Shoe Pool Lifecycle (`FR-011`)**: Because different agents make different decisions (e.g. hitting vs standing), tables deplete cards at different rates. When a table reaches cut-card penetration and finishes its round, it checks whether the next shoe generation ($G$) is cached in the pool. If yes, it adopts a pristine clone of that generation; if not, the orchestrator deterministically generates it (`seed = base_seed + G * 1000`), caches it, and assigns it. This guarantees that all tables experience the exact same shoe sequences across generations despite depletion rate desynchronization.
4. **Composite Stopping Criteria (`FR-012`)**: Simulations terminate automatically upon reaching `max_rounds`, when all participating agents become bankrupt (bankroll below table minimum bet), or via explicit programmatic `stop()`.

---

### 3. Architecture & Implemented Components

The simulation orchestrator is structured modularly across 6 core modules and an isolated agents subpackage in `backend/app/simulation/`:

| Module | Core Responsibility |
| :--- | :--- |
| [`types.py`](../backend/app/simulation/types.py) | Domain value containers and enums (`SessionStatus`, `EntityType`, `SimulationConfig`, `DecisionContext`, `AgentDecision`, `SimulationMetrics`, `SimulationSession`). |
| [`interfaces.py`](../backend/app/simulation/interfaces.py) | Public runtime protocols (`DecisionProvider`, `OrchestratorController`, `EventPublisher`) and domain exceptions (`SimulationError`, `SimulationStateError`, `AgentFaultError`, `IllegalAgentActionError`). |
| [`events.py`](../backend/app/simulation/events.py) | Strongly typed telemetry event model (`SimulationEvent`, `EventType`) and asynchronous event bus (`EventEmitter`) supporting both sync and coroutine listeners with listener error isolation. |
| [`agents/basic_strategy.py`](../backend/app/simulation/agents/basic_strategy.py) | Pure mathematical `BasicStrategyAgent` executing optimal blackjack game theory for hard totals, soft totals, pair splits, and surrender. |
| [`agents/fake_agents.py`](../backend/app/simulation/agents/fake_agents.py) | Temporary mock entities (`FakeJevAgent`, `FakeLayaAgent`) with simulated latencies, confidence metrics, and deterministic fault/illegal action injection. |
| [`shoe_pool.py`](../backend/app/simulation/shoe_pool.py) | Session-level generational shoe repository (`ShoePool`) maintaining deterministic shoe sequence cloning across tables. |
| [`table.py`](../backend/app/simulation/table.py) | Isolated `EntityTable` linking a `DecisionProvider` with a `BlackjackRound`, transforming state to `DecisionContext`, enforcing legal action validation, and tracking bankroll/bankruptcy. |
| [`orchestrator.py`](../backend/app/simulation/orchestrator.py) | Core `SimulationOrchestrator` implementing `OrchestratorController` with `asyncio` round barrier, flow control (`pause`/`resume`/`step_round`/`step_turn`/`stop`), fail-fast transition to `PAUSED_ERROR`, and retry recovery. |
| [`__init__.py`](../backend/app/simulation/__init__.py) | Package public API exports. |

---

### 4. Verification & Testing

All 31 tasks (T001–T031) defined in [`tasks.md`](../specs/002-simulation-orchestrator/tasks.md) were implemented and verified with **41 automated tests across 10 test modules**:

- **[`test_simulation_events.py`](../backend/tests/test_simulation_events.py)** (8 tests): Subscription, sync/async dispatch, wildcard listeners, chronological ordering, listener exception isolation, unsubscribe.
- **[`test_simulation_agents.py`](../backend/tests/test_simulation_agents.py)** (5 tests): Protocol compliance, basic strategy hard/soft/split decisions, fake latency simulation, fault/illegal action injection.
- **[`test_simulation_shoe_pool.py`](../backend/tests/test_simulation_shoe_pool.py)** (4 tests): Seed derivation, caching and reuse across generations, independent deck isolation, inter-generation variance.
- **[`test_simulation_table.py`](../backend/tests/test_simulation_table.py)** (5 tests): Initialization, metrics tracking, round execution, illegal action trapping, shoe adoption, bankruptcy elimination.
- **[`test_simulation_orchestrator.py`](../backend/tests/test_simulation_orchestrator.py)** (4 tests): Controller protocol compliance, identical initial table conditions, 10-round synchronized multi-agent MVP execution, 100% reproducibility across identical seeds (`SC-003`).
- **[`test_simulation_flow_control.py`](../backend/tests/test_simulation_flow_control.py)** (4 tests): Non-blocking pause, state preservation, resume, single round stepping, single turn stepping, stop cancellation.
- **[`test_simulation_faults.py`](../backend/tests/test_simulation_faults.py)** (3 tests): Fail-fast pause to `PAUSED_ERROR` upon provider exception or illegal action, peer table state preservation, recovery via `retry_failed_entity()`.
- **[`test_simulation_shoe_lifecycle.py`](../backend/tests/test_simulation_shoe_lifecycle.py)** (2 tests): Cross-table shoe generation sharing upon differing cut-card crossing, early termination when all agents bankrupt.
- **[`test_simulation_telemetry.py`](../backend/tests/test_simulation_telemetry.py)** (2 tests): Chronological stream verification and schema validation across all milestone events (`SESSION_STARTED`, `ROUND_STARTED`, `CARD_DEALT`, `DECISION_APPLIED`, `ROUND_SETTLED`, `SESSION_COMPLETED`).
- **[`test_simulation_quickstart.py`](../backend/tests/test_simulation_quickstart.py)** (4 tests): End-to-end execution of all 4 scenarios from [`quickstart.md`](../specs/002-simulation-orchestrator/quickstart.md).

```text
=== Test Execution Summary ===
tests.test_simulation_events         : 8 passed
tests.test_simulation_agents         : 5 passed
tests.test_simulation_shoe_pool      : 4 passed
tests.test_simulation_table          : 5 passed
tests.test_simulation_orchestrator   : 4 passed
tests.test_simulation_flow_control   : 4 passed
tests.test_simulation_faults         : 3 passed
tests.test_simulation_shoe_lifecycle : 2 passed
tests.test_simulation_telemetry      : 2 passed
tests.test_simulation_quickstart     : 4 passed
----------------------------------------
Simulation Tests : 41 passed, 0 failed (100% Pass Rate)
Engine Tests     : 35 passed, 0 failed (100% Pass Rate)
Total Codebase   : 76 passed, 0 failed (100% Pass Rate)
```

---

### 5. Technical Highlights

1. **Zero-Contamination Generational Caching**: Tables mutating their shoes during play never affect peer tables or future generations because `ShoePool.get_shoe_for_generation()` stores the generation template and yields isolated deep clones.
2. **True Non-Blocking Dual-Mode Flow Control**: `step_round()` and `step_turn()` operate seamlessly whether the simulation loop is driven directly step-by-step or running as a concurrent background `asyncio` task that is paused and resumed.
3. **Decoupled Architecture**: Real model integrations (TypeSafe System One and local PyTorch/ONNX inference) can be dropped in simply by implementing the 3-member `DecisionProvider` protocol without modifying orchestrator or table internals.

---

### 6. Documentation & Artifacts Delivered

- [`docs/Simulation_Orchestrator.md`](Simulation_Orchestrator.md): Comprehensive architectural reference, class diagrams, state machine transitions, telemetry schema, and guide for integrating real decision models.
- [`docs/session_logs.md`](session_logs.md): This log entry.
- [`specs/002-simulation-orchestrator/`](../specs/002-simulation-orchestrator/): Full Spec-Kit artifacts (`spec.md`, `plan.md`, `tasks.md`, `data-model.md`, `research.md`, `quickstart.md`, `contracts/orchestrator_api.md`, `checklists/requirements.md`).

---

## Session: 2026-10-11

**Focus**: Basic Strategy Player, Hi-Lo Bet Sizing, and Positional Comparison Oracle  
**Branch**: `main` (Feature directory: `specs/003-basic-strategy-player/`)  
**Status**: Completed & Verified (100% Test Pass Rate, 22 test modules, 0 failures)

---

### 1. Executive Summary

Today's session designed, implemented, and verified the **Full Blackjack Basic Strategy Player** and the **Decision Comparison Oracle** residing in `backend/app/models/`. Following the Spec-Kit methodology (`specify` → `clarify` → `plan` → `tasks` → `implement`), the player strictly encodes the mathematical decision matrices from `docs/Estrategia Optima.md` with zero guessing or heuristics.

In addition to playing autonomously at its own table, the system provides a standalone evaluation oracle (`DecisionComparator`) that evaluates other players (such as Jev and Laya) in their specific table context. Even when tables hold completely different cards (e.g., Basic Strategy plays 12 vs 5 while Jev plays 15 vs 2), the oracle benchmarks Jev's move against what Basic Strategy dictates for 15 vs 2, as well as benchmarking opening bets against the Hi-Lo True Count bet spread.

The mockup agent in `backend/app/simulation/agents/basic_strategy.py` was replaced with this complete player, maintaining 100% backward compatibility and zero test regressions.

---

### 2. Implemented Architecture (`backend/app/models/`)

| Module | Core Responsibility |
| :--- | :--- |
| [`strategy_matrices.py`](../backend/app/models/strategy_matrices.py) | 100% matrix representation of Hard Totals (8–17+ vs 2–A), Soft Totals (A,2–A,9 vs 2–A with `Ds` double-else-stand fallback), Pair Splitting with DAS `Y/N` resolution, Surrender rules, and insurance rejection. |
| [`card_counter.py`](../backend/app/models/card_counter.py) | `HiLoCardCounter` tracking running count (+1, 0, -1), half-deck resolution deck estimation, True Count calculation, and count reset triggers. |
| [`schemas.py`](../backend/app/models/schemas.py) | Evaluation domain models: `DecisionCategory`, `DecisionComparison`, `BetComparison`, `BetSpreadConfig`. |
| [`decision_comparator.py`](../backend/app/models/decision_comparator.py) | Positional `DecisionComparator` oracle evaluating any agent's decision (`evaluate_turn_decision`) and bet spread sizing (`evaluate_round_bet`). |
| [`basic_strategy_player.py`](../backend/app/models/basic_strategy_player.py) | Concrete `BasicStrategyPlayer` conforming to `DecisionProvider`, supporting `get_bet()`, `reset_count()`, and card observation. |
| [`simulation/table.py`](../backend/app/simulation/table.py) | Updated `EntityTable` integrating inline turn evaluations, tracking `optimal_decisions` vs `suboptimal_decisions`, and calling `provider.get_bet()` and `reset_count()`. |
| [`simulation/orchestrator.py`](../backend/app/simulation/orchestrator.py) | Updated orchestrator embedding `comparison` metadata inside `DECISION_APPLIED` event payloads. |
| [`simulation/agents/basic_strategy.py`](../backend/app/simulation/agents/basic_strategy.py) | Re-exports `BasicStrategyPlayer` as `BasicStrategyAgent` for seamless backward compatibility. |

---

### 3. Verification & Testing

- **Strategy Matrices Tests** (`test_strategy_matrices.py`): 100% cell verification across Hard, Soft, Pair splitting, Surrender, and DAS fallback rules.
- **Card Counter Tests** (`test_card_counter.py`): Running count, True Count scaling, and reset lifecycle.
- **Basic Strategy Player Tests** (`test_basic_strategy_player.py`): Decision correctness and insurance rejection.
- **Bet Sizing Tests** (`test_basic_strategy_betting.py`): True Count spread scaling ($1 \times \text{min\_bet}$ when $TC \le 0$, $N \times \text{min\_bet}$ when $TC > 0$, max spread cap, bankroll safety).
- **Decision Comparator Tests** (`test_decision_comparator.py`): Positional turn benchmarking and bet delta evaluation.
- **Quickstart Scenarios** (`test_basic_strategy_quickstart.py`): End-to-end verification of all scenarios in `quickstart.md`.
- **Regression Suite**: All 22 test modules across the engine and simulation packages passed with 100% pass rate.

---

## Session: 2026-10-11 (Part 2)

**Focus**: Database Schema, SQLAlchemy 2.0 AsyncIO ORM, Orchestrator Telemetry Persistence Listener, Replay Repository, and Run Exporter  
**Branch**: `main` (Feature directory: `specs/004-database-persistence/`)  
**Status**: Completed & Verified (100% Test Pass Rate, 118/118 tests passed, 0 failures, Ruff checks clean)

---

### 1. Executive Summary

Today's session designed, implemented, and verified the complete **Database Schema & Simulation Telemetry Persistence Layer** residing in `backend/app/persistence/`. Built to persist all simulation executions from the multi-agent orchestrator, the relational schema models all 15 domain entities defined in `docs/Diseño Base de Datos (Modelo ER).md`.

The persistence layer runs against the dedicated PostgreSQL 16 Alpine container (`app_db`) via SQLAlchemy 2.0 AsyncIO and `asyncpg`. It operates strictly as an asynchronous telemetry sink and persistent record store, decoupled from the core deterministic blackjack engine (satisfying Constitution Principles I & V).

Key capabilities delivered:
1. **15-Entity Relational Schema**: 18 PostgreSQL ENUMs, UUID primary keys, composite uniqueness constraints (`UNIQUE (simulation_id, player_type)`, `UNIQUE (round_id, player_session_id)`, etc.), and complete `ON DELETE CASCADE` across all child entities.
2. **Real-Time Asynchronous Telemetry Listener**: `SimulationPersistenceListener` attaches to orchestrator `EventEmitter`, translating stream events into relational entities (`CardEvent`, `Decision` with `optimal_reference_action` & `agrees_with_optimal`, `ModelResponse`, `Bet`, and `BankrollTransaction`) without blocking engine execution.
3. **Atomic Round-Boundary Batch Flushing**: In-memory event buffering committing at round boundaries or in configurable batches of $N$ rounds, safeguarding against partial state on simulation pause or abort.
4. **Historical Replay & Analytical Repository**: `RunRepository` providing full chronological round replay timelines (`get_round_replay`), dynamic player benchmark calculations (`get_player_benchmark_summary` computing win rates, ROI, and basic strategy agreement percentage without stale columns), and clean cascade deletion.
5. **Run Archival JSON Exporter**: `RunExporter` serializing complete runs into structured artifacts at `/data/runs/[timestamp]/run_data.json`.

---

### 2. Implemented Architecture (`backend/app/persistence/`)

| Module | Core Responsibility |
| :--- | :--- |
| [`database.py`](../backend/app/persistence/database.py) | Singleton async SQLAlchemy 2.0 engine, async sessionmaker factory, connection pooling with pre-ping, `check_db_health()`, and `init_db()` auto-provisioning. |
| [`models.py`](../backend/app/persistence/models.py) | All 18 PostgreSQL ENUMs and 15 ORM domain models across 6 domains (Execution, Participants, Shoes, Game Flow, Decisions/AI, Economy) with `TIMESTAMPTZ` and `ON DELETE CASCADE`. |
| [`listener.py`](../backend/app/persistence/listener.py) | `SimulationPersistenceListener` subscribing to orchestrator `EventEmitter`, buffering round events and performing atomic batch commits with error-state capture. |
| [`repositories.py`](../backend/app/persistence/repositories.py) | `RunRepository` providing run CRUD, cascading hard deletions, chronological round replay timeline queries, and dynamic benchmark metrics calculations. |
| [`exporter.py`](../backend/app/persistence/exporter.py) | `RunExporter` with `EntityJSONEncoder` serializing complete 15-entity hierarchies into self-contained `run_data.json` artifacts. |
| [`migrations/init_schema.sql`](../backend/app/persistence/migrations/init_schema.sql) | Standalone idempotent DDL migration script with all 18 ENUMs, 15 tables, 12 query indexes, and foreign keys. |
| [`__init__.py`](../backend/app/persistence/__init__.py) | Package public API exports. |

---

### 3. Verification & Testing

All 24 tasks (T001–T024) defined in [`tasks.md`](../specs/004-database-persistence/tasks.md) were executed and verified against the PostgreSQL container:

- **[`test_persistence_schema.py`](../backend/tests/test_persistence_schema.py)** (4 tests): Table creation, composite unique constraints, check constraints, foreign key cascades, and eager loaded relationship queries.
- **[`test_persistence_listener.py`](../backend/tests/test_persistence_listener.py)** (4 tests): Attach/detach lifecycle, synthetic round event translation, AI telemetry capture (`optimal_reference_action`, `agrees_with_optimal`, `ModelResponse`), live orchestrator execution, and error recovery.
- **[`test_persistence_exporter.py`](../backend/tests/test_persistence_exporter.py)** (1 test): Complete 15-entity JSON export matching run structure.
- **[`test_persistence_repository.py`](../backend/tests/test_persistence_repository.py)** (3 tests): Run CRUD, chronological round replay timeline ordering, and dynamic benchmark calculation.
- **[`test_persistence_quickstart.py`](../backend/tests/test_persistence_quickstart.py)** (2 tests): End-to-end execution of all 5 quickstart scenarios.
- **Full Project Test Suite**: 118/118 passed in 1.69s across engine, simulation, models, and persistence.
- **Static Analysis & Linting**: `ruff check` passed with zero errors across `app/persistence` and all persistence test suites.

---

## Session: 2026-10-11

**Focus**: Local Laya Deep Learning Model Integration, Docker Host-Bridge Connectivity, TypeSafe System One Dynamic Schemas, Multi-Phase Game Decisions, and Fault Resilience  
**Branch**: `main` (Feature directory: `specs/005-laya-agent-integration/`)  
**Status**: Completed & Verified (100% Test Pass Rate, 153/153 tests passed, 30 new Laya tests, Ruff checks clean)

---

### 1. Executive Summary

Today's session designed, implemented, and verified the complete **Laya Decision Agent Integration & Container Host Bridge** residing in `backend/app/integrations/laya/`. This integration connects the blackjack simulation engine running inside a Docker container (`app_backend`) with the user's host-native Laya deep learning inference service (`http://127.0.0.1:1234` or custom port via `LAYA_BASE_URL` in `.env`).

The integration strictly adheres to the TypeSafe System One JSON protocol defined in `docs/Laya_Example_Body.md` and fulfills Constitution Principles I, II, III, and V:
- **Clean Decoupling**: All Laya transport and inference code resides isolated in `backend/app/integrations/laya/`.
- **Dynamic Host Bridging**: Seamless container-to-host routing via `extra_hosts: ["host.docker.internal:host-gateway"]` in `docker-compose.yml` and automatic URL normalization inside `LayaConfig`.
- **Dynamic Situational Schemas**: `LayaSchemaBuilder` constructs context-aware natural language game state and filters choice options strictly to legal actions across all 7 situational contracts (1A Paired No Surrender, 1B Paired Surrender, 2A Standard No Surrender, 2B Standard Surrender, 3 Multi-Card Draw, 4 Insurance Offer, 5 Discrete Bet Sizing).
- **Multi-Phase Autonomy**: `LayaAgent` participates in pre-deal round wagering (`1x`, `2x`, `4x`, `8x` of dynamic table minimum bet), insurance side bets, and all in-hand tactical decisions (Hit, Stand, Double, Split, Surrender).
- **Fault Resilience & Pause Compliance (RNF-02)**: On host disconnects, server timeouts, or malformed payloads, errors translate to `AgentFaultError`, pausing all active tables synchronously (`PAUSED_ERROR`) without data loss, and allowing clean resume once connectivity is restored.

---

### 2. Implemented Architecture (`backend/app/integrations/laya/`)

| Module | Core Responsibility |
| :--- | :--- |
| [`config.py`](../backend/app/integrations/laya/config.py) | `LayaConfig` reading `LAYA_BASE_URL` from `.env`, bounded timeouts/retries, and automatic container normalization (`127.0.0.1`/`localhost` $\to$ `host.docker.internal`). |
| [`schemas.py`](../backend/app/integrations/laya/schemas.py) | TypeSafe System One Pydantic v2 transport models (`QuestionType`, `ChoiceQuestion`, `SystemOneRequest`, `ChoiceAnswer`, `SystemOneResponse`, `LayaHealthStatus`, `HandSituationType`). |
| [`client.py`](../backend/app/integrations/laya/client.py) | Async HTTP client (`httpx.AsyncClient`) supporting `GET /health` and `POST /v1/systemone` with high-precision latency timing and `AgentFaultError` error translation. |
| [`builder.py`](../backend/app/integrations/laya/builder.py) | `LayaSchemaBuilder` detecting tactical hand situations and dynamically assembling prompts and criteria adhering to table rules and legal actions. |
| [`agent.py`](../backend/app/integrations/laya/agent.py) | `LayaAgent` satisfying `DecisionProvider` protocol (`name="Laya"`, `entity_type=EntityType.LAYA`, `get_decision()`, `get_bet()`, `get_insurance()`). |
| [`__init__.py`](../backend/app/integrations/laya/__init__.py) | Package public API exports. |

---

### 3. Verification & Testing

All 24 tasks (T001–T024) across 7 phases were executed and verified against Docker container tests:

- **[`test_laya_config.py`](../backend/tests/test_laya_config.py)** (7 tests): Default configurations, `.env` port overrides, Docker environment detection, and host URL normalization.
- **[`test_laya_client.py`](../backend/tests/test_laya_client.py)** (6 tests): Health probe `/health` parsing, system one requests, network timeout and connection error translation to `AgentFaultError`.
- **[`test_laya_schemas.py`](../backend/tests/test_laya_schemas.py)** (8 tests): Situational schemas for Contracts 1A, 1B, 2A, 2B, 3, 4 (Insurance), and 5 (Betting with dynamic `min_bet`).
- **[`test_laya_agent.py`](../backend/tests/test_laya_agent.py)** (6 tests): `get_decision()` across all blackjack actions, `get_bet()` discrete multipliers, `get_insurance()` choices, and telemetry metadata packaging.
- **[`test_laya_simulation.py`](../backend/tests/test_laya_simulation.py)** (3 tests): Full orchestrator multi-agent simulation verifying `PAUSED_ERROR` on fault, table bankroll preservation, resume execution, and `DecisionComparator` evaluation.
- **[`test_health.py`](../backend/tests/test_health.py)** (3 tests): `/health` and `/health/laya` API diagnostic endpoints.
- **Full Project Test Suite**: 153/153 passed in 2.13s across engine, simulation, persistence, and Laya integration.
- **Static Analysis & Linting**: `ruff check` passed with zero errors across all Laya modules and test suites.



---

## Session: 2026-10-12

**Focus**: Remote TypeSafe Jev System One Model Integration, Bearer Token Authentication, Rate Limit Backoff, Situational Schemas, and Tri-Entity Benchmarking  
**Branch**: `main` (Feature directory: `specs/006-jev-agent-integration/`)  
**Status**: Completed & Verified (100% Test Pass Rate, 173/173 unit/integration tests passed, 30 new Jev tests, 0 failures)

---

### 1. Executive Summary

Today's session designed, implemented, and verified the complete **TypeSafe Jev Decision Agent Integration** residing in `backend/app/integrations/jev/`. This integration connects the blackjack simulation engine with TypeSafe's flagship System One remote model **Jev** via `POST https://api.typesafe.ai/v1/systemone` using Bearer token authentication configured in `.env` (`TYPESAFE_API_KEY`, `TYPESAFE_API_URL`, `TYPESAFE_MODEL`).

Following the Spec-Kit methodology (`specify` → `plan` → `tasks` → `implement`), Jev now acts as a full-fledged autonomous decision provider within the multi-agent orchestrator alongside Laya and Optimal Basic Strategy:
- **Clean Decoupling**: All remote transport, authentication, and serialization code resides isolated in `backend/app/integrations/jev/`.
- **Dynamic Situational Schemas**: `JevSchemaBuilder` constructs context-aware natural language game states with the mandatory `"model"` parameter, constraining candidate actions strictly to legal actions across all situations (Initial Paired Hand with/without Surrender, Initial Standard Hand with/without Surrender, Multi-Card Draw, Insurance Offer, and Pre-Deal Wager Sizing).
- **Multi-Phase Autonomy**: `JevAgent` participates in round opening bet sizing (`1x`, `2x`, `4x`, `8x` of table minimum bet), insurance side bets, and all in-hand tactical decisions (Hit, Stand, Double, Split, Surrender).
- **Fault Resilience & Rate Limit Backoff (RNF-02)**: Implemented automated exponential backoff retry on HTTP 429 (`Too Many Requests`) and HTTP 529 (`Overloaded`). On persistent errors or timeouts, cleanly raises `AgentFaultError`, transitioning the simulation to `PAUSED_ERROR` synchronously without state or bankroll corruption.
- **Unified Telemetry & Benchmarking**: Captures model revision, token usage (`input_tokens`, `output_tokens`), latency, confidence score, and probability distributions, mapping them to `decisions` and `model_responses` (`provider=ModelProvider.SYSTEM_ONE`) while benchmarking decisions in real time against the `DecisionComparator`.

---

### 2. Implemented Architecture (`backend/app/integrations/jev/`)

| Module | Core Responsibility |
| :--- | :--- |
| [`config.py`](../backend/app/integrations/jev/config.py) | `JevConfig` reading `TYPESAFE_API_KEY`, `TYPESAFE_API_URL`, `TYPESAFE_MODEL`, timeouts, and retry limits dynamically from `.env`. |
| [`schemas.py`](../backend/app/integrations/jev/schemas.py) | Pydantic v2 transport models (`QuestionType`, `ChoiceQuestion`, `SystemOneRequest`, `ChoiceAnswer`, `UsageInfo`, `SystemOneResponse`, `JevHealthStatus`, `HandSituationType`). |
| [`client.py`](../backend/app/integrations/jev/client.py) | Async HTTP client (`httpx.AsyncClient`) supporting `GET /health` and `POST /v1/systemone` with Bearer auth, exponential backoff retries, and `AgentFaultError` error translation. |
| [`builder.py`](../backend/app/integrations/jev/builder.py) | `JevSchemaBuilder` generating dynamic situational prompts matching table rules, bankroll, and legal actions. |
| [`agent.py`](../backend/app/integrations/jev/agent.py) | `JevAgent` satisfying `DecisionProvider` protocol (`name="Jev"`, `entity_type=EntityType.JEV`, `get_decision()`, `get_bet()`, `get_insurance()`). |
| [`__init__.py`](../backend/app/integrations/jev/__init__.py) | Package public API exports. |

---

### 3. Verification & Testing

All 24 tasks (T001–T024) defined in `specs/006-jev-agent-integration/tasks.md` were executed and verified with 30 new automated tests across 5 test modules:

- **[`test_jev_config.py`](../backend/tests/test_jev_config.py)** (4 tests): Default configurations, `.env` parameter overrides, URL helpers, and boundary validation.
- **[`test_jev_schemas.py`](../backend/tests/test_jev_schemas.py)** (8 tests): Situational schemas for Contracts 1A, 1B, 2A, 2B, 3, 4 (Insurance), and 5 (Betting with dynamic `min_bet`).
- **[`test_jev_client.py`](../backend/tests/test_jev_client.py)** (9 tests): Health probe `/health`, Bearer authentication header, retry on HTTP 429/529, token usage parsing, and error translation.
- **[`test_jev_agent.py`](../backend/tests/test_jev_agent.py)** (7 tests): `get_decision()` across all actions, illegal action fallback, `get_bet()` discrete multipliers, `get_insurance()` choices, and telemetry metadata packaging.
- **[`test_jev_simulation.py`](../backend/tests/test_jev_simulation.py)** (2 tests): Multi-agent simulation verifying `PAUSED_ERROR` on fault, table bankroll preservation, resume execution, and `DecisionComparator` evaluation.
- **Full Project Test Suite**: 174 passed, 0 failed, 10 skipped (container DB) across engine, simulation, persistence, Laya, and Jev integrations.

---

### 4. Post-Verification Bugfix & Developer Ergonomics Update

- **Issue Resolved**: When users executed the Scenario 4 quickstart snippet (`await orchestrator.run()`), `AttributeError: 'SimulationOrchestrator' object has no attribute 'run'` was encountered.
- **Root Cause**: `SimulationOrchestrator` implemented `start()` but lacked an async `run()` convenience method returning `self.session`, and `SimulationSession` lacked a `rounds_completed` alias for `current_round`.
- **Changes Applied**:
  - Added `async def run(self) -> SimulationSession` to [`backend/app/simulation/orchestrator.py`](../backend/app/simulation/orchestrator.py) to launch `start()` and cleanly return the final session snapshot.
  - Added `@property def rounds_completed(self) -> int` to `SimulationSession` in [`backend/app/simulation/types.py`](../backend/app/simulation/types.py).
  - Added `register_entity = add_entity` alias to `SimulationOrchestrator` for backward compatibility across both Laya and Jev quickstart scripts.
  - Added unit test `test_orchestrator_run_convenience_method` in [`backend/tests/test_simulation_orchestrator.py`](../backend/tests/test_simulation_orchestrator.py).
  - Verified 100% pass rate: 174 passed, 0 failed, 10 skipped.

---

### 5. Automated `.env` Loading & Authentication Fix (HTTP 403 Resolution)

- **Issue Resolved**: When executing `JevAgent()` in Python scripts, inference calls failed with HTTP 403 `{"detail":{"error_type":"authentication_error","message":"Must supply an API key! Check your request and try again."}}`.
- **Root Cause**: Python processes executing outside of Docker did not automatically parse the workspace `.env` file into `os.environ`. Consequently, `os.getenv("TYPESAFE_API_KEY", "")` evaluated to empty string, suppressing the `Authorization` header.
- **Changes Applied**:
  - Implemented automatic `.env` discovery and loading in [`backend/app/integrations/jev/config.py`](../backend/app/integrations/jev/config.py) using `find_dotenv(usecwd=True)` and recursive parent directory lookup with `override=False`.
  - Added `@field_validator("api_key")` to sanitize whitespace and quotes.
  - Added dual authentication headers in [`backend/app/integrations/jev/client.py`](../backend/app/integrations/jev/client.py): `Authorization: Bearer <key>` and `x-api-key: <key>`.
  - Added pre-flight check in `send_systemone()` raising `AgentFaultError` immediately if `api_key` is missing.
  - Handled both HTTP 401 and HTTP 403 as non-retryable authentication failures.
  - Added tests `test_send_systemone_auth_error_403` and `test_send_systemone_missing_api_key` in [`backend/tests/test_jev_client.py`](../backend/tests/test_jev_client.py).
  - Verified 100% pass rate: 176 passed, 0 failed, 10 skipped.

---

## Session: 2026-10-13

**Focus**: FastAPI REST & Native WebSockets API, Real-Time Basic Strategy Deviation Analytics, Interactive Simulation Flow Control, Streaming Hierarchical JSON Exports, and Cascading Database Purge  
**Branch**: `main` (Feature directory: `specs/007-simulation-frontend-api/`)  
**Status**: Completed & Verified (100% Test Pass Rate, 35/35 new API tests, 211/211 total backend tests passed, 0 failures)

---

### 1. Executive Summary

Today's session designed, implemented, and verified the complete **Simulation Frontend API & Export Service** residing in `backend/app/api/`. Following the Spec-Kit methodology (`specify` → `clarify` → `plan` → `tasks` → `implement`), this feature bridges the web frontend client with the underlying blackjack simulation engine, persistence layer, and external AI agent providers (TypeSafe Jev, local Laya, and Optimal Basic Strategy).

Key architectural and functional requirements implemented:
1. **Configurable Experiment Provisioning (`POST /api/simulations`)**: Validates all house rules from `docs/Reglas de BlackJack.md` (S17/H17, 3:2 payout, American Peek vs ENHC, insurance, late/early/no surrender, DAS, RSA, max split hands, 1–8 decks, cut-card penetration, burn cards, bankrolls, and betting limits). Performs pre-flight health checks for Jev and Laya, provisioning isolated tables sharing identical starting shoes derived from a deterministic seed.
2. **Native WebSocket Real-Time Telemetry (`/ws/simulations/{session_id}`)**: Streams live round telemetry over native FastAPI WebSockets (`fastapi.WebSocket` without third-party wrappers like socketio). Emits an immediate `SESSION_SNAPSHOT` on connection, starts orchestrator execution without dropped events, and broadcasts turn-by-turn frames (`DECISION_MADE` and `ROUND_SETTLED`).
3. **Real-Time Strategy Deviation Analytics**: Enriches decision frames with full basic strategy comparison oracle metadata (`optimal_action`, `actual_action`, `category`, `is_optimal`, `reasoning`). Aggregates running deviation statistics segmented across Hard Totals, Soft Totals, Pair Splits, Surrenders, and Bet Spread deltas, streamed in `ROUND_SETTLED` frames and queryable via `GET /api/simulations/{session_id}/deviations`.
4. **Interactive Flow Control & Fault Recovery**: Bidirectional command dispatching via WebSocket and REST fallback (`POST /api/simulations/{session_id}/control`): `pause`, `resume`, `step` (round/turn), `set_speed` (0 ms to 2,000 ms), `stop`, and RNF-02 `retry` on `PAUSED_ERROR`.
5. **Historical Runs Catalog & Inspection**: `GET /api/simulations` paginated catalog querying past runs and active in-memory sessions; `GET /api/simulations/{session_id}` detailed run inspection with table rules snapshot and benchmarks.
6. **Hierarchical JSON Exports**: `GET /api/export/simulations/{session_or_run_id}` serving single-run hierarchical JSON documents matching the `RunExporter` schema; `GET /api/export/database` streaming the full database archive sequentially to guarantee memory stays strictly below 256 MB.
7. **Database Purge & Reset**: `DELETE /api/database` and `POST /api/database/clear` executing atomic `TRUNCATE TABLE ... CASCADE` across all 15 relational tables with safety guards rejecting execution with HTTP 409 Conflict if simulations are actively running.

---

### 2. Specification & Key Clarifications Resolved

1. **Native WebSockets strictly (no socketio)**: All bidirectional streaming leverages native `fastapi.WebSocket` and `starlette.websockets` directly, minimizing transport overhead and container complexity.
2. **Real-Time Strategy Deviation Metrics (`FR-023`, `FR-024`)**: Required aggregating turn-by-turn decisions and comparing them against the Basic Strategy oracle, computing live optimality rates, category breakdowns, and bet spread discrepancies.
3. **Dual-Trigger Simulation Lifecycle**: Visualized simulations initialize in `status="INITIALIZING"`. Connecting to `/ws/simulations/{session_id}` emits `SESSION_SNAPSHOT` and triggers immediate execution so clients receive all events from round 1 without dropped frames. For headless or REST testing, `POST /api/simulations/{session_id}/start` serves as the explicit execution trigger.
4. **Database Streaming Export (Memory Guard)**: `RunExporter.export_all_runs_streaming()` queries run IDs and streams individual run documents sequentially as JSON chunks, ensuring server memory remains strictly under 256 MB even for massive datasets.
5. **Database Purge Conflict Guard**: Database truncation is blocked with HTTP 409 Conflict when any simulation session is `RUNNING`, `PAUSED`, or `PAUSED_ERROR`.

---

### 3. Architecture & Implemented Components (`backend/app/api/`)

| Module | Core Responsibility |
| :--- | :--- |
| [`schemas.py`](../backend/app/api/schemas.py) | Pydantic v2 validation models (`TableRulesConfig`, `SimulationConfigRequest`, `SimulationResponse`, `SimulationListItem`, `SimulationListResponse`, `DecisionComparisonPayload`, `CategoryDeviationStats`, `BetSpreadDeviationStats`, `EntityDeviationStats`, `SimulationDeviationsResponse`, `PurgeDatabaseResponse`, `ControlCommandRequest`). |
| [`manager.py`](../backend/app/api/manager.py) | `SimulationManager` handling in-memory session registry (`ActiveSessionRecord`), async background orchestrator loop, WebSocket connection registry, real-time deviation aggregation, and lifecycle control. |
| [`simulations.py`](../backend/app/api/simulations.py) | REST endpoints for experiment provisioning (`POST /api/simulations`), explicit start (`POST /{id}/start`), paginated historical catalog (`GET /api/simulations`), detailed inspection (`GET /{id}`), deviation analytics (`GET /{id}/deviations`), and flow control (`POST /{id}/control`). |
| [`websocket.py`](../backend/app/api/websocket.py) | Native WebSocket endpoint `/ws/simulations/{session_id}` handling client connections, snapshot emission, auto-start, telemetry broadcasting, and client command handling (`pause`, `resume`, `step`, `set_speed`, `stop`, `retry`). |
| [`export.py`](../backend/app/api/export.py) | Data export endpoints (`GET /api/export/simulations/{session_or_run_id}` and `GET /api/export/database`) with `Content-Disposition` attachment headers and streamed responses. |
| [`database.py`](../backend/app/api/database.py) | Maintenance endpoints (`DELETE /api/database`, `POST /api/database/clear`) executing atomic table purge with active simulation conflict guard. |
| [`router.py`](../backend/app/api/router.py) | Consolidated API router mounting all sub-routers (`health`, `simulations`, `websocket`, `export`, `database`). |
| [`main.py`](../backend/app/main.py) | Application entry point configuring CORS middleware for frontend origins, OpenAPI tags metadata, and mounting `api_router`. |
| [`persistence/exporter.py`](../backend/app/persistence/exporter.py) | Extended `RunExporter` with `get_run_export_dict()` and `export_all_runs_streaming()` yielding JSON chunks incrementally. |
| [`persistence/repositories.py`](../backend/app/persistence/repositories.py) | Extended `RunRepository` with `purge_all_tables()` executing atomic multi-table `TRUNCATE TABLE ... CASCADE` across all 15 relational tables with fallback. |

---

### 4. Verification & Testing

All 35 tasks (T001–T035) defined in `specs/007-simulation-frontend-api/tasks.md` were executed and verified against automated test suites:

- **[`test_api_schemas.py`](../backend/tests/test_api_schemas.py)** (6 tests): Valid configurations, default rules, boundary validations (e.g. `min_bet > max_bet`, penetration bounds), and deviation schemas.
- **[`test_api_simulations.py`](../backend/tests/test_api_simulations.py)** (11 tests): Experiment provisioning (HTTP 201), rule validation failures (HTTP 422), identical shoe seeding, REST start trigger, historical runs listing with pagination, detailed inspection with DB fallback, deviations query, flow control commands, and RNF-02 fault recovery retry.
- **[`test_api_websocket.py`](../backend/tests/test_api_websocket.py)** (3 tests): WebSocket handshake, 4404 close on non-existent session, live event broadcasting (`SESSION_SNAPSHOT`, `DECISION_MADE` with comparison, `ROUND_SETTLED` with running deviations), and interactive WebSocket flow control (`pause`, `set_speed`, `resume`).
- **[`test_api_export.py`](../backend/tests/test_api_export.py)** (5 tests): Single-run JSON export (HTTP 200 with schema, HTTP 404 on missing run), active session ID resolution, attachment headers, and full database streaming archive.
- **[`test_api_database.py`](../backend/tests/test_api_database.py)** (4 tests): Atomic purge via DELETE and POST alias, verification of 15 cleared tables, and active simulation conflict guard (HTTP 409).
- **[`test_api_quickstart.py`](../backend/tests/test_api_quickstart.py)** (6 tests): End-to-end verification covering all 6 scenarios from `quickstart.md`.

```text
=== API Test Execution Summary ===
tests.test_api_schemas    : 6 passed
tests.test_api_simulations: 11 passed
tests.test_api_websocket  : 3 passed
tests.test_api_export     : 5 passed
tests.test_api_database   : 4 passed
tests.test_api_quickstart : 6 passed
----------------------------------------
API Tests        : 35 passed, 0 failed (100% Pass Rate)
Pre-Existing     : 176 passed, 10 skipped (container DB)
Total Codebase   : 211 passed, 10 skipped, 0 failed (100% Pass Rate)
```

---

### 5. Technical Highlights & Critical Fixes

1. **Async get_decision Coroutine Dispatch**: In `BasicStrategyPlayer`, `get_decision()` is an `async def` coroutine. When delegating decisions in mock and orchestrator adapters, calls must be explicitly awaited (`await self.delegate.get_decision(...)`), preventing unhandled coroutine warnings and premature `PAUSED_ERROR` halts.
2. **Zero Dropped Events via Immediate Snapshot**: Connecting to `/ws/simulations/{session_id}` immediately delivers the complete `SESSION_SNAPSHOT` and begins round loop execution, guaranteeing clients never miss initial deals or decisions regardless of client startup timing.
3. **Memory-Guarded Database Archival**: `RunExporter.export_all_runs_streaming()` streams historical runs sequentially as formatted JSON chunks, maintaining flat memory usage (< 256 MB) regardless of database volume.
4. **Defensive Multi-Dialect Table Purge**: `RunRepository.purge_all_tables()` executes atomic PostgreSQL `TRUNCATE TABLE ... CASCADE` across all 15 tables with an automatic fallback for dialect differences during unit testing.

---

### 6. Documentation & Artifacts Delivered

- [`specs/007-simulation-frontend-api/`](../specs/007-simulation-frontend-api/): Complete Spec-Kit artifacts (`spec.md`, `plan.md`, `tasks.md`, `data-model.md`, `quickstart.md`, `contracts/rest-api.yaml`, `contracts/websocket-protocol.md`, `checklists/requirements.md`).
- [`api_implementation_walkthrough.md`](../api_implementation_walkthrough.md): Comprehensive implementation walkthrough artifact.
- [`docs/session_logs.md`](session_logs.md): This log entry.


