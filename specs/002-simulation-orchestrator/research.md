# Phase 0 Research: Simulation Orchestrator

**Feature**: [spec.md](spec.md)  
**Package**: `backend/app/simulation/`  
**Date**: 2026-10-10

---

## 1. Concurrency & Synchronization Architecture

### Decision: `asyncio` Task Grouping with Synchronous Round Barriers
- **Choice**: Cooperative asynchronous execution using Python's `asyncio` (`asyncio.gather` / `TaskGroup`).
- **Rationale**:
  - Each decision entity table operates independently within an active round. An agent's decision request (whether fake, local model, or future remote API) is inherently non-blocking or I/O bound.
  - Cooperative concurrency allows all 3 tables to request and apply player actions concurrently.
  - A round barrier awaits completion of all active tables before settling and advancing to round $N+1$.
  - In-flight cancellations and immediate pause requests can be cleanly managed using `asyncio.Event` without thread synchronization overhead or GIL deadlocks.
- **Alternatives Considered**:
  - *Multi-threading (`concurrent.futures.ThreadPoolExecutor`)*: Thread management introduces unnecessary synchronization complexity and risk of race conditions over shared event buses and shoe pools.
  - *Strict Turn Lockstep*: Blocking all tables while waiting for a single entity's turn creates synthetic latency coupling and fails to simulate true independent tables.

---

## 2. Agent Provider Abstraction & Fake Agent Isolation

### Decision: Clean Protocol in `simulation.interfaces` with Isolated `simulation.agents` Module
- **Choice**:
  - Define `DecisionProvider` as a `@runtime_checkable Protocol` in `backend/app/simulation/interfaces.py`.
  - Place temporary fake agents in a dedicated sub-package `backend/app/simulation/agents/fake_agents.py`.
  - Implement a mathematical Basic Strategy baseline in `backend/app/simulation/agents/basic_strategy.py`.
- **Rationale**:
  - Directly satisfies the user constraint: *"The fake agents will be temporary and they should be easily removable in exchange for real agents implementations in future specs."*
  - The orchestrator only ever depends on the `DecisionProvider` protocol. When real remote Jev (API) and local Laya (ONNX/PyTorch) providers are implemented in future features, they simply implement `DecisionProvider` and plug in without modifying the orchestrator, tables, or event bus.
  - Fake agents can simulate realistic agent traits: response latencies, confidence scores (0.0 to 1.0), and configurable error injection (e.g. simulated timeout or provider exception) for testing fault recovery.
- **Alternatives Considered**:
  - *Hardcoding fake logic directly in EntityTable*: Violates Single Responsibility and Constitution Principle III (Provider Abstraction). Would require invasive refactoring later.

---

## 3. Generational Shoe Pool Lifecycle

### Decision: Session-Level `ShoePool` with Indexed Shoe Generations
- **Choice**:
  - Create a `ShoePool` class that manages deterministically generated shoe instances indexed by generation number: `generation_index = 0, 1, 2, ...`.
  - When Table A crosses the cut-card penetration threshold and completes its round, it requests the next shoe generation (e.g. `generation_index = 1`) from `ShoePool`.
  - If `ShoePool` does not yet contain generation 1, it deterministically generates it (using a seeded PRNG sequence derived from the session seed: `seed + generation_index`) and stores it.
  - When Table B and Table C subsequently cross their cut cards in later rounds, they request generation 1, find it cached in `ShoePool`, and consume the exact same card sequence.
- **Rationale**:
  - Directly fulfills the user clarification: differing agent actions cause tables to deplete cards at different rates. If Table A splits 3 times and draws 8 cards, it crosses the cut card earlier than Table B which stood on 2 cards.
  - Eliminates premature reshuffling of tables that haven't crossed the cut card while guaranteeing that all tables consume identical shoe generations.
- **Alternatives Considered**:
  - *Synchronized global reshuffle at round end*: Forces tables with 80% cards remaining to prematurely discard their shoe just because another table hit repeatedly. Violates casino realism.
  - *Completely independent uncoordinated shoes*: Causes tables to diverge in shoe composition, violating Constitution Principle II (Tri-Entity Synchronization & Experiment Isolation).

---

## 4. Execution Flow Control (Pause, Resume, Step, Stop)

### Decision: Event-Driven State Machine with `asyncio.Event` Pause Flag
- **Choice**:
  - Orchestrator tracks lifecycle state: `INITIALIZING`, `RUNNING`, `PAUSED`, `PAUSED_ERROR`, `STOPPED`, `COMPLETED`.
  - Maintain an internal `_pause_event: asyncio.Event` (set = running, cleared = paused).
  - Between turns and at the start of each round, tables check `_pause_event.wait()`.
  - `pause()` clears the event. `resume()` sets the event.
  - `step_round()` sets a single-round latch, executes one round, and pauses.
  - `step_turn()` advances one active turn and pauses.
  - `stop()` cancels ongoing execution and transitions to `STOPPED`.
- **Rationale**:
  - Clean, non-blocking cooperative pause without polling or CPU spinning.
  - Guarantees zero state loss or corrupted hands upon pausing.
- **Alternatives Considered**:
  - *Polling loop with `time.sleep`*: Wasteful CPU cycles and unresponsive during long pauses.

---

## 5. Telemetry & Event Broadcasting Architecture

### Decision: In-Memory `EventEmitter` with Strongly Typed Dataclass Events
- **Choice**:
  - Pure in-memory observer pattern (`EventEmitter`) supporting asynchronous and synchronous listener callbacks.
  - Hierarchical event dataclasses: `SimulationEvent` base with subclasses:
    - `SessionStartedEvent`, `SessionCompletedEvent`, `SessionPausedEvent`, `SessionResumedEvent`, `SessionErrorEvent`
    - `RoundStartedEvent`, `TurnRequestedEvent`, `DecisionAppliedEvent`, `RoundSettledEvent`, `ShoeReshuffledEvent`
- **Rationale**:
  - Decouples the simulation engine from file exporters, WebSocket servers, and PostgreSQL persistence (Constitution Principle V).
  - Allows tests to register an `InMemoryEventCollector` to assert exact chronological event sequences.
- **Alternatives Considered**:
  - *Direct database insertion during turn execution*: Violates architectural isolation and slows down in-memory benchmarks.
  - *Raw dictionary events*: Lacks static type safety and prone to payload schema drift.
