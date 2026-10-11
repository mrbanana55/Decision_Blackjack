# Feature Specification: Simulation Orchestrator

**Feature Branch**: `002-simulation-orchestrator`

**Created**: 2026-10-09

**Input**: User description: "Let's create the orchestratos. This will be in charge of managing simulations and rounds, handling agents and turns, pause and reanudation control, administrate shoes lifecycle and sessions, Handle Jev and laya errors, broadcast events for persistence and visualization. We should end up with a full simulation with fake agents, we should not depend on a real API or a GUI."

## Clarifications

### Session 2026-10-09
- Q: How should the orchestrator step through player turns across the three tables during an active round? (FR-005) → A: Concurrent Table Execution with Round Barrier: Each entity table executes its round turns asynchronously and independently; the orchestrator synchronizes at the round completion barrier before dealing round $N+1$. If any table faults, all tables halt immediately.
- Q: When an agent provider encounters an error (timeout, exception, or invalid action), what is the default automated recovery behavior? (FR-009) → A: Immediate Pause & Await Controller (Fail-Fast): Instantly pause all 3 tables synchronously in `PAUSED_ERROR` state, preserve all state, broadcast error telemetry, and wait for controller intervention (`retry` or `abort`).
- Q: What are the primary termination/stopping criteria supported for automated simulation runs? (FR-012) → A: Composite Stopping Criteria: Supports stopping when reaching configured `max_rounds`, when all agents are bankrupt/eliminated, or upon receiving an explicit programmatic `stop()` command.
- Q: When tables deplete shoe cards at differing rates, how is shoe reshuffling coordinated? (FR-011) → A: Generational Shoe Pool: When a table crosses the cut card and completes its round, it checks the session shoe pool for a saved shoe for that generation index. If one exists, it adopts it; if not, a new deterministic shoe is generated, saved in the pool for peer tables, and assigned to the table. Peer tables retrieve and adopt this saved shoe when they reach their own cut cards.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-Agent Simulation with Identical Initial Conditions (Priority: P1)

As a simulation researcher or benchmark engineer, I want to execute a synchronized simulation comparing multiple decision entities (Jev, Laya, and Optimal Strategy) playing isolated Blackjack tables with identical initial conditions (same seed, rules, and shoe composition), so that decision quality and bankroll trajectories can be scientifically compared without external UI or API dependencies.

**Why this priority**: Foundational core capability. Comparative AI evaluation requires orchestrating multiple tables under identical, fair initial conditions with pluggable fake agents.

**Independent Test**: Can be tested independently by initializing the orchestrator with three fake agents (simulated Jev, simulated Laya, and rule-based Optimal Strategy), running a configured number of rounds (e.g., 10 rounds), and verifying that all three tables start from identical card permutations and play to completion headlessly.

**Acceptance Scenarios**:

1. **Given** a simulation configured with 3 decision entities and a fixed seed, **When** the simulation starts, **Then** the orchestrator initializes 3 independent table instances, each sharing identical initial shoe configurations and table rules.
2. **Given** an active round across all tables, **When** an entity's turn arrives, **Then** the orchestrator queries that entity's provider for an action given its observable table state, applies the decision to that table, and advances the turn.
3. **Given** tables with varying player actions (e.g., one agent hits while another stands), **When** all active tables conclude their player turns, **Then** the dealer hand resolves independently per table, each table settles its round, and no table advances to the next round until all active tables have settled.
4. **Given** completed rounds, **When** inspecting simulation state, **Then** bankroll trajectories, decisions made, and round outcomes are tracked independently per entity.

---

### User Story 2 - Execution Flow Control (Pause, Resume, Step, and Stop) (Priority: P1)

As a simulation controller, I want full control over the execution flow—including pause, resume, single-step advancement, and cancellation—so that simulations can be paused for inspection, stepped through turn-by-turn during debugging, or safely stopped.

**Why this priority**: Crucial for operational control and automated experiment supervision, as mandated by Constitution Principle II.

**Independent Test**: Can be tested independently by launching an automated multi-round simulation, issuing a pause command mid-execution, verifying all tables halt synchronously without losing state, stepping a single round or turn, and then resuming to completion.

**Acceptance Scenarios**:

1. **Given** an actively running multi-round simulation, **When** a pause command is issued, **Then** all tables halt execution at the current turn/round boundary, transition simulation state to `PAUSED`, and preserve all in-flight round and shoe state.
2. **Given** a paused simulation, **When** a resume command is issued, **Then** the orchestrator resumes execution from the exact point of interruption without state corruption or duplicate actions.
3. **Given** a paused simulation, **When** a step command is issued, **Then** the orchestrator advances exactly one turn or one round and immediately returns to the paused state.
4. **Given** an active or paused simulation, **When** an abort/stop command is issued, **Then** the orchestrator halts remaining rounds, transitions state to `STOPPED`, and finalizes session metrics up to the interruption point.

---

### User Story 3 - Agent Provider Fault Handling and Synchronous Recovery (Priority: P2)

As a system operator, I want the orchestrator to detect and isolate agent failures (such as simulated timeouts, provider exceptions, or invalid action responses from fake Jev or Laya) by pausing all tables synchronously and offering controlled recovery, so that a failure in one model does not corrupt comparative benchmark validity or crash the entire simulation.

**Why this priority**: Directly enforces Constitution Principle III and Requirement RNF-02 (graceful pause with state preservation upon remote or local provider failures).

**Independent Test**: Can be tested independently by injecting a simulated fault (e.g., timeout or exception) into one fake agent, observing that the orchestrator halts all three tables synchronously, records the error event, and allows a retry or abort command.

**Acceptance Scenarios**:

1. **Given** an active simulation, **When** an agent provider raises an error or times out during a turn request, **Then** the orchestrator catches the fault, immediately pauses all tables synchronously, and emits a structured error telemetry event.
2. **Given** a simulation paused due to an agent error, **When** a retry command is issued after resolving the transient issue, **Then** the orchestrator re-requests the decision from that agent and resumes normal progression.
3. **Given** an agent returning an action that is illegal for its current hand, **When** the orchestrator validates the action against the engine, **Then** the orchestrator treats the illegal action as a provider fault, pauses progression, and flags the invalid decision.

---

### User Story 4 - Multi-Round Generational Shoe Lifecycle & Session Administration (Priority: P2)

As a benchmark orchestrator, I want the orchestrator to administrate shoe lifecycles through a shared generational shoe pool—detecting cut-card penetration per table, generating reshuffled shoes on first need and caching them for peer tables, and evaluating session termination conditions—so that long-running multi-shoe simulations execute reproducibly with identical shoe sequences across entities.

**Why this priority**: Enforces Constitution Principle IV (Seeded Reproducibility) across multi-round, multi-shoe experiments while properly accounting for differing card consumption rates across agent decision paths.

**Independent Test**: Can be tested independently by running multi-round simulations where tables draw differing numbers of cards per round, verifying that when one table crosses the cut card and needs a new shoe, it generates and saves that reshuffled shoe in the session shoe pool; when peer tables subsequently reach their cut card, they retrieve and adopt that saved shoe rather than generating a divergent one.

**Acceptance Scenarios**:

1. **Given** multiple entity tables depleting shoe cards at different rates, **When** Table A crosses the cut-card penetration threshold and concludes its active round, **Then** the orchestrator checks if a reshuffled shoe for that generation index (e.g. Shoe #2) is already saved in the session shoe pool; if none exists, it generates a new deterministic shoe, saves it in the pool for other tables, and assigns it to Table A.
2. **Given** a peer table (Table B) that later crosses its cut-card penetration threshold in a subsequent round, **When** Table B requires a reshuffled shoe, **Then** the orchestrator checks the session shoe pool, finds the previously saved shoe for that generation, and assigns it to Table B so all tables experience the identical shoe sequence.
3. **Given** a simulation configured with a maximum round count (e.g., 50 rounds), **When** all 50 rounds settle, **Then** the orchestrator transitions session status to `COMPLETED` and produces a session summary.
4. **Given** an entity whose bankroll reaches zero or falls below the minimum table bet, **When** the round settles, **Then** that entity is flagged as `ELIMINATED`, while remaining solvent entities continue until session completion.

---

### User Story 5 - Event Broadcasting for Persistence & Telemetry (Priority: P3)

As an analytical logger or visualization subscriber, I want the orchestrator to broadcast structured, strongly typed domain events for all key simulation milestones, so that downstream modules (database persistence, file exporters, live telemetry, and UI clients) can observe the simulation without coupling to the orchestrator core.

**Why this priority**: Required by Constitution Principle V (Telemetry, Structured Persistence & Batch Safety) to decouple execution from persistence and real-time visualization.

**Independent Test**: Can be tested independently by attaching an in-memory event collector to the orchestrator, executing rounds, and verifying that all lifecycle events (session start, round start, turn request, decision applied, round settled, shoe reshuffled, session completed) are emitted in strict chronological order with complete payload metadata.

**Acceptance Scenarios**:

1. **Given** an active simulation with registered event listeners, **When** any lifecycle event occurs (round deal, player decision, settlement, pause, error), **Then** the orchestrator synchronously or asynchronously broadcasts a structured event containing timestamp, session ID, table ID, entity name, and event payload.
2. **Given** multiple registered listeners (e.g., an in-memory history log and a metrics collector), **When** events are broadcast, **Then** all listeners receive the events without mutating orchestrator state.

---

### Edge Cases

- **Desynchronized Split/Hit Depletion**: What happens when one agent splits into multiple hands and draws 6 cards while another stands on two cards, causing shoe penetration to be reached on Table A before Table B or Table C?
  - *Resolution*: Table A finishes its active round with its current shoe. When preparing for the next round, Table A checks the session shoe pool for the next shoe generation (e.g., Shoe #2). Because none exists yet, a new deterministic reshuffled shoe is generated, stored in the session pool for that generation index, and assigned to Table A. Table B and Table C continue playing from Shoe #1 until they each independently cross their cut-card thresholds; upon reaching the cut card, each table checks the pool, retrieves the pre-generated Shoe #2, and adopts it. This guarantees all tables play through the exact same shoe generations without forcing a premature reshuffle on tables that haven't reached the cut card yet.
- **Entity Bankruptcy Asynchrony**: What happens when Jev goes bankrupt on Round 12 while Laya and Optimal Strategy remain solvent?
  - *Resolution*: The bankrupt entity's table is marked as inactive/busted; the remaining entities continue playing rounds until the session's overall stopping condition is satisfied.
- **Pause Requested Mid-Decision**: What happens if a pause request arrives while an asynchronous agent decision is pending?
  - *Resolution*: The orchestrator allows the in-flight decision to complete and apply to the hand, but immediately freezes progression before initiating the next turn or dealer draw.
- **Provider Exception on Retry**: What happens if an agent fails repeatedly when retrying?
  - *Resolution*: The orchestrator keeps the simulation in the `PAUSED_ERROR` state and allows the controller to either abort the entire simulation or permanently eliminate the failing agent.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The orchestrator MUST manage the lifecycle of a simulation session through explicit lifecycle states: `INITIALIZING`, `RUNNING`, `PAUSED`, `PAUSED_ERROR`, `STOPPED`, and `COMPLETED`.
- **FR-002**: The orchestrator MUST support concurrent, isolated execution of multiple decision entities (specifically Jev, Laya, and Optimal Strategy) playing independent table instances governed by the core Blackjack engine.
- **FR-003**: The orchestrator MUST ensure all entity tables originate from identical initial conditions (same seed, table rules, and initial bankroll) to guarantee comparative experimental validity.
- **FR-004**: The orchestrator MUST advance rounds synchronously, preventing any table from proceeding to round $N+1$ until all active tables have settled round $N$.
- **FR-005**: The orchestrator MUST execute entity tables concurrently with a round barrier, allowing each active table to execute its player decisions asynchronously while guaranteeing that all active tables complete and settle round $N$ before the orchestrator initiates round $N+1$. If any entity encounters a fault, all tables MUST halt immediately.
- **FR-006**: The orchestrator MUST define an abstract `DecisionProvider` interface that accepts observable table/hand state and returns a structured action decision (`HIT`, `STAND`, `DOUBLE`, `SPLIT`, `SURRENDER`, `INSURANCE_ACCEPT`, `INSURANCE_DECLINE`) with confidence and latency metadata.
- **FR-007**: The orchestrator MUST provide standalone, fake decision providers (e.g., Mock Jev, Mock Laya, Rule-based Optimal Strategy) so that complete simulations run headlessly with zero external API key or network dependencies.
- **FR-008**: The orchestrator MUST provide programmatic controls to `start()`, `pause()`, `resume()`, `step_turn()`, `step_round()`, and `stop()` the simulation.
- **FR-009**: The orchestrator MUST enforce a fail-fast fault recovery policy: when any agent provider encounters an error (timeout, unhandled exception, or illegal action response), the orchestrator MUST immediately pause all tables synchronously in `PAUSED_ERROR` state, preserve all state, emit a structured error telemetry event, and await controller intervention (explicit `retry` or `abort`).
- **FR-010**: The orchestrator MUST validate all agent decisions against the engine's legal actions before application, treating illegal decisions as provider faults without corrupting table state.
- **FR-011**: The orchestrator MUST administrate a generational shoe pool across tables: when a table crosses the cut-card threshold and finishes its round, it MUST check if a reshuffled shoe for that generation index is already saved in the pool. If a saved shoe exists, the table MUST adopt it; if not, the orchestrator MUST deterministically generate the new shoe, save it in the pool for peer tables, and assign it to the requesting table.
- **FR-012**: The orchestrator MUST enforce composite simulation stopping criteria, automatically concluding a session when reaching the configured `max_rounds` limit, when all participating agents are bankrupt (bankroll below table minimum bet), or upon receiving an explicit programmatic `stop()` command.
- **FR-013**: The orchestrator MUST implement an event broadcasting system (`EventEmitter` / observer pattern) publishing strongly typed domain events for simulation milestones.
- **FR-014**: Event payloads MUST include ISO timestamps, session identifiers, entity identifiers, round numbers, table indices, event types, and serializable domain state.
- **FR-015**: The orchestrator MUST execute entirely in-memory and MUST NOT depend on a database connection, web framework, or graphical user interface for its core execution and testing.

---

### Key Entities

- **SimulationSession**: Configuration and state container for an active benchmark experiment (session ID, seed, rules, max rounds, active state, start/end timestamps).
- **EntityTable**: Pairing of a specific `DecisionProvider` (Jev, Laya, Optimal Strategy) with its dedicated `BlackjackRound` table, tracking cumulative bankroll, round count, and metrics.
- **ShoePool**: Session-level container managing numbered shoe generations (`Shoe #1`, `Shoe #2`, ...) across simulation tables to ensure identical shoe sequence consumption despite desynchronized card depletion rates.
- **DecisionProvider**: Protocol for decision agents, exposing an asynchronous or synchronous `get_decision(context)` method returning an `AgentDecision`.
- **AgentDecision**: Data container holding the chosen `Action`, decision confidence (0.0 to 1.0), latency in milliseconds, and optional reasoning metadata.
- **SimulationEvent**: Base type for all broadcasted telemetry messages (`SessionStarted`, `RoundStarted`, `CardDealt`, `TurnRequested`, `DecisionMade`, `RoundSettled`, `ShoeReshuffled`, `SimulationPaused`, `SimulationResumed`, `SimulationError`, `SessionCompleted`).
- **FakeAgent**: Test implementation of `DecisionProvider` capable of deterministic rule-following, pre-programmed decision scripting, or simulated error injection.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An automated simulation comparing 3 fake entities can execute 100 complete, synchronized rounds headlessly in under 2 seconds without external dependencies.
- **SC-002**: 100% of injected agent errors (timeouts, exceptions) trigger an immediate, synchronous pause across all tables with zero corrupted hand states or dropped rounds.
- **SC-003**: Given identical seeds and deterministic agent implementations, repeated simulation runs produce byte-for-byte identical round sequences, decisions, and final bankroll values (100% reproducible).
- **SC-004**: When pausing an active simulation mid-execution, 100% of in-flight table and shoe states are preserved, and resuming completes all remaining rounds with zero skipped turns.
- **SC-005**: 100% of defined simulation lifecycle transitions emit valid, strongly typed telemetry events captured by registered listeners in chronological order.

---

## Assumptions

- **Fake Agents Default**: Default agent providers implemented for this module will run locally using rule-based algorithms, mock scripts, or Basic Strategy tables to eliminate remote API dependencies. Real LLM/API integration will plug into the `DecisionProvider` interface in a subsequent feature.
- **In-Memory Event Bus**: Event dispatching will operate via an in-memory publish/subscribe mechanism; external message brokers (Redis, WebSocket servers, Kafka) are outside the scope of this core engine orchestrator.
- **Single Thread / Async Event Loop**: The orchestrator is designed for Python asynchronous execution (`asyncio`), allowing cooperative turn progression, timeout management, and non-blocking event dispatching.
- **Independent Dealer Hands**: While all tables receive identical initial shoe permutations, dealer cards drawn during dealer turns depend on each table's unique player draw depletion.
