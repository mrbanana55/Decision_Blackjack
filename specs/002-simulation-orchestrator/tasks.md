# Tasks: Simulation Orchestrator

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Package**: `backend/app/simulation/`  
**Date**: 2026-10-10

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the simulation package structure, domain types, configuration models, and public protocols.

- [x] T001 Initialize package directories `backend/app/simulation/` and `backend/app/simulation/agents/` with empty `__init__.py` files
- [x] T002 [P] Implement all enums and value containers (`SessionStatus`, `EntityType`, `SimulationConfig`, `DecisionContext`, `AgentDecision`, `SimulationMetrics`) in `backend/app/simulation/types.py`
- [x] T003 [P] Implement abstract protocols (`DecisionProvider`, `OrchestratorController`, `EventPublisher`) and domain exceptions (`SimulationError`, `SimulationStateError`, `AgentFaultError`, `IllegalAgentActionError`) in `backend/app/simulation/interfaces.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure and provider primitives (Event bus, Agent abstractions, Generational Shoe pool) that MUST be complete before multi-agent user stories can proceed.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 [P] Create unit tests for event broadcasting in `backend/tests/test_simulation_events.py` verifying subscription, sync/async listener dispatch, and chronological ordering
- [x] T005 [P] Implement `EventType` enum, `SimulationEvent` dataclass hierarchy, and `EventEmitter` bus in `backend/app/simulation/events.py`
- [x] T006 [P] Create unit tests for agent providers in `backend/tests/test_simulation_agents.py` verifying `BasicStrategyAgent` decisions, fake latencies, confidence metrics, and fault simulation
- [x] T007 Implement mathematical `BasicStrategyAgent` conforming to `DecisionProvider` in `backend/app/simulation/agents/basic_strategy.py`
- [x] T008 Implement temporary `FakeJevAgent` and `FakeLayaAgent` (with configurable latency and fault simulation) in `backend/app/simulation/agents/fake_agents.py`
- [x] T009 [P] Create unit tests for generational shoe pool in `backend/tests/test_simulation_shoe_pool.py` verifying deterministic seed derivation and cached shoe retrieval across generations
- [x] T010 Implement `ShoePool` generational shoe repository in `backend/app/simulation/shoe_pool.py`

**Checkpoint**: Foundation ready - event bus, agent providers, and shoe pool are operational.

---

## Phase 3: User Story 1 - Multi-Agent Simulation with Identical Initial Conditions (Priority: P1) 🎯 MVP

**Goal**: Execute synchronized simulations comparing multiple decision entities (Jev, Laya, and Optimal Strategy) playing isolated table instances initialized with identical seeds, table rules, and initial bankroll, advancing with synchronous round barriers.

**Independent Test**: Can be tested independently by launching an automated simulation with 3 fake agents, executing 10 complete rounds headlessly, and verifying that all tables start from identical card permutations, play concurrently, and settle synchronously at each round boundary.

### Tests for User Story 1 ⚠️

- [x] T011 [P] [US1] Create unit tests for EntityTable in `backend/tests/test_simulation_table.py` verifying isolated `BlackjackRound` integration, turn querying, decision execution, and bankroll tracking
- [x] T013 [P] [US1] Create multi-agent simulation unit tests in `backend/tests/test_simulation_orchestrator.py` verifying concurrent table execution, identical initial conditions, and round barrier synchronization

### Implementation for User Story 1

- [x] T012 [US1] Implement `EntityTable` in `backend/app/simulation/table.py` wrapping a `BlackjackRound` instance with its attached `DecisionProvider`, turn execution, and metrics tracking
- [x] T014 [US1] Implement core `SimulationOrchestrator` in `backend/app/simulation/orchestrator.py` (`add_entity`, session initialization, concurrent round runner with `asyncio` round barrier, and round settlement)
- [x] T015 [US1] Export public simulation API in `backend/app/simulation/__init__.py` and `backend/app/simulation/agents/__init__.py`

**Checkpoint**: User Story 1 (MVP) is fully functional! 3 fake agents play synchronized Blackjack rounds headlessly without API or UI dependencies.

---

## Phase 4: User Story 2 - Execution Flow Control (Pause, Resume, Step, and Stop) (Priority: P1)

**Goal**: Provide non-blocking operational flow control (`pause`, `resume`, `step_round`, `step_turn`, `stop`) preserving 100% of in-flight table and shoe states.

**Independent Test**: Can be verified by launching a multi-round simulation, issuing `pause()`, verifying that all tables halt without state loss, executing `step_round()`, and resuming to completion.

### Tests for User Story 2 ⚠️

- [x] T016 [P] [US2] Create flow control unit tests in `backend/tests/test_simulation_flow_control.py` verifying pause, state preservation, resume, single round stepping, single turn stepping, and stop cancellation

### Implementation for User Story 2

- [x] T017 [US2] Implement non-blocking `pause()` and `resume()` flow control using `asyncio.Event` in `backend/app/simulation/orchestrator.py`
- [x] T018 [US2] Implement `step_round()` and `step_turn()` single-advancement logic in `backend/app/simulation/orchestrator.py`
- [x] T019 [US2] Implement `stop()` cancellation and session metrics finalization in `backend/app/simulation/orchestrator.py`

**Checkpoint**: User Stories 1 AND 2 work together seamlessly with full pause/resume/step controls.

---

## Phase 5: User Story 3 - Agent Provider Fault Handling & Synchronous Recovery (Priority: P2)

**Goal**: Detect and isolate agent failures (timeouts, unhandled exceptions, illegal actions) by immediately pausing all tables in `PAUSED_ERROR` state and providing clean recovery via `retry_failed_entity()`.

**Independent Test**: Can be verified by injecting simulated errors into fake Jev or Laya, verifying all tables halt synchronously without corrupted hands, and confirming that retrying resolves the fault and completes the simulation.

### Tests for User Story 3 ⚠️

- [x] T020 [P] [US3] Create fault handling unit tests in `backend/tests/test_simulation_faults.py` verifying timeout handling, provider exceptions, illegal action rejections, synchronous pause, and retry recovery

### Implementation for User Story 3

- [x] T021 [US3] Implement agent decision validation against engine legal actions and provider exception trapping in `backend/app/simulation/table.py`
- [x] T022 [US3] Implement fail-fast transition to `PAUSED_ERROR`, error telemetry emission, and `retry_failed_entity()` recovery in `backend/app/simulation/orchestrator.py`

**Checkpoint**: Fault tolerance and fail-fast recovery are operational and verifiable.

---

## Phase 6: User Story 4 - Multi-Round Generational Shoe Lifecycle & Session Administration (Priority: P2)

**Goal**: Administrate generational shoe pool across desynchronized tables (generating next-generation shoes on first need and caching for peer tables), tracking bankruptcy elimination, and enforcing composite stopping criteria.

**Independent Test**: Can be verified by running simulations with varied agent decision paths and low penetration thresholds, verifying that tables crossing the cut card retrieve and reuse identical shoe generations from the pool.

### Tests for User Story 4 ⚠️

- [x] T023 [P] [US4] Create generational shoe lifecycle and session administration tests in `backend/tests/test_simulation_shoe_lifecycle.py`

### Implementation for User Story 4

- [x] T024 [US4] Integrate generational `ShoePool` retrieval and independent cut-card tracking inside `backend/app/simulation/table.py` and `backend/app/simulation/orchestrator.py`
- [x] T025 [US4] Implement entity bankruptcy elimination (`is_eliminated=True` when bankroll < min_bet) and composite stopping criteria (`max_rounds`, all bankrupt, or manual stop) in `backend/app/simulation/orchestrator.py`

**Checkpoint**: Long-running multi-shoe simulations maintain strict reproducibility across differing table depletion rates.

---

## Phase 7: User Story 5 - Event Broadcasting for Persistence & Telemetry (Priority: P3)

**Goal**: Broadcast strongly typed domain events for all key simulation milestones (session start, round deal, turn request, decision applied, round settled, shoe reshuffled, session completed) to enable persistence and live visualization.

**Independent Test**: Can be verified by attaching an in-memory event listener and asserting that complete, strongly typed event payloads are emitted in exact chronological order across multi-round simulations.

### Tests for User Story 5 ⚠️

- [x] T026 [P] [US5] Create telemetry and event broadcasting tests in `backend/tests/test_simulation_telemetry.py` verifying chronological ordering and schema compliance for all simulation event types

### Implementation for User Story 5

- [x] T027 [US5] Wire event emission across all session, table, round, turn, decision, and error milestones in `backend/app/simulation/orchestrator.py` and `backend/app/simulation/table.py`

**Checkpoint**: Complete simulation telemetry is broadcast and decoupled from persistence backends.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Validation against quickstart scenarios, code quality audits, and documentation.

- [x] T028 [P] Validate quickstart validation scenarios from `specs/002-simulation-orchestrator/quickstart.md` in `backend/tests/test_simulation_quickstart.py`
- [x] T029 [P] Run syntax and static analysis checks across the new package via `py_compile` and `ruff check backend/app/simulation`
- [x] T030 Execute complete simulation test suite verifying 100% test pass rate via `pytest backend/tests/test_simulation_*.py -v`
- [x] T031 Update `docs/Simulation_Orchestrator.md` detailing architecture, interfaces, and instructions for swapping fake agents with real providers

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can begin immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001–T003) - BLOCKS all User Stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion (T004–T010). Delivers MVP.
- **User Story 2 (Phase 4)**: Depends on User Story 1 completion (T011–T015).
- **User Story 3 (Phase 5)**: Depends on User Story 1 completion (T011–T015); can run sequentially after US2.
- **User Story 4 (Phase 6)**: Depends on User Story 1 & ShoePool foundational tasks (T009–T010).
- **User Story 5 (Phase 7)**: Depends on User Story 1 & Event foundational tasks (T004–T005).
- **Polish (Phase 8)**: Depends on all user stories being completed.

### Parallel Opportunities

- **Phase 1**: T002 (`types.py`) and T003 (`interfaces.py`) can be implemented in parallel.
- **Phase 2**: T004/T005 (Events), T006/T007/T008 (Agents), and T009/T010 (ShoePool) can be developed in parallel.
- **Phase 3**: T011 (EntityTable tests) and T013 (Orchestrator tests) can be written in parallel.
- **Phase 4**: T016 (Flow control tests) can be written in parallel with earlier tasks.
- **Phase 5**: T020 (Fault tests) can be created in parallel.
- **Phase 6**: T023 (Shoe lifecycle tests) can be created in parallel.
- **Phase 7**: T026 (Telemetry tests) can be created in parallel.
- **Phase 8**: T028 (`test_simulation_quickstart.py`) and T029 (`ruff check`) can run in parallel.

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1 (Setup: types, interfaces).
2. Complete Phase 2 (Foundational: events, basic strategy, fake agents, shoe pool).
3. Complete Phase 3 (User Story 1: `EntityTable`, `SimulationOrchestrator` concurrent round execution with round barrier).
4. **STOP and VALIDATE**: Run `test_simulation_orchestrator.py`. The simulation engine can now run 3 isolated tables headlessly with fake agents!

### Incremental Delivery
1. Add Phase 4 (User Story 2: Pause, resume, step, stop).
2. Add Phase 5 (User Story 3: Fail-fast error handling and retry).
3. Add Phase 6 (User Story 4: Generational shoe pool & composite stopping criteria).
4. Add Phase 7 (User Story 5: Event broadcasting for persistence/visualization).
5. Run Phase 8 (Polish, quickstart validation, and documentation).
