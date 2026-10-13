# Feature Specification: Simulation Frontend API & Export Service

**Feature Branch**: `007-simulation-frontend-api`  
**Created**: 2026-10-12  
**Status**: Draft  
**Input**: User description: "Let's make an API to connect backend with the frontend. We need the API to communicate the whole simulation with the frontend, showing every decision for each player (Jev, Laya and basic strategy). We also need to post the initial configuration, the user will be able to set different things like rounds, simulations, and all the changeable rules shown inside docs/Reglas de BlackJack.md. Another thing we need is to be able to export the data from the database into a JSON. We should be able to export the whole database or only the current simulation(s)."

---

## Clarifications

### Session 2026-10-12
- Q: Which real-time communication protocol should the API provide to stream live simulation events and handle flow control with the frontend? → A: Option A (WebSocket - single bidirectional connection for both real-time telemetry streaming and client flow control commands).
- Q: When a user launches multiple simulations (num_simulations > 1), how should the backend execute and stream them to the frontend? → A: Option A (Execution Mode Selection: support Visualized mode with turn-by-turn/round-by-round streaming, and Fast Batch mode with unthrottled background execution and simulation-level progress events).
- Q: What schema structure should the exported JSON files have when downloading simulation data? → A: Option A (Hierarchical Document - nested JSON hierarchy matching RunExporter containing Run metadata, configuration, player summaries, and sequential round histories with their hands, bets, and model decisions).
- Q: Should the WebSocket connection allow the frontend client to dynamically adjust simulation playback speed during live execution? → A: Option A (Dynamic Speed Adjustment: client can send a `set_speed` command over WebSocket with variable delay between 0 ms unthrottled and 2,000 ms at any time).
- Q: How should the API handle simulation initialization if one of the external AI agents (e.g., Laya local service or TypeSafe Jev API) is unavailable or unconfigured? → A: Option A (Flexible Selection with Pre-Flight Validation: client chooses any entity subset from Jev, Laya, and Optimal; system performs pre-flight health checks only on requested entities and supports an optional `mock_mode` flag for offline testing).
- Q: How should the API support clearing all database records across every table? → A: Dedicated clear endpoint (`DELETE /api/database` / `POST /api/database/clear`) executing cascading deletion across all 15 relational tables with safety guards against clearing while simulations are actively running.
- Q: How should the API provide strategy deviation information comparing Jev and Laya to Basic Strategy? → A: The API must compute and stream real-time strategy deviation statistics via WebSocket (embedding the full comparison details—optimal action, actual action, decision category, and reasoning—in every decision event, plus cumulative deviation metrics per player in round settlement frames) and expose a dedicated query endpoint (`GET /api/simulations/{session_id}/deviations`) reporting overall optimality rates, deviation counts, and category breakdowns (Hard Totals, Soft Totals, Pair Splits, Surrenders, and bet spread deltas).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configurable Experiment Initialization & Casino Rules Setup (Priority: P1)

As a researcher or frontend user, I want to submit a complete simulation configuration from the web interface—specifying round counts, simulation quantities, random seeds, participating decision entities, and all changeable casino rules defined in the house rules document—so that I can launch controlled, reproducible multi-agent Blackjack experiments under custom or casino-standard conditions.

**Why this priority**: Without the ability to define and submit simulation parameters and table rules, neither the frontend nor the simulation engine can initiate customized experimental runs. This is the entry point for all system functionality.

**Independent Test**: Can be verified by submitting a valid simulation configuration payload with custom rules (e.g., S17 vs H17, 3:2 payout, late surrender, 6 decks, 75% penetration), verifying that the backend validates the parameters, creates the isolated entity tables, and returns a session handle confirming initialization with identical starting conditions.

**Acceptance Scenarios**:

1. **Given** a client submits a valid configuration payload specifying 100 rounds, 1 simulation, seed 42, active entities (Jev, Laya, Optimal Basic Strategy), and custom table rules (S17, 3:2 payout, DAS enabled, Late Surrender, 6 decks, $10 min bet, $1,000 bankroll), **When** the configuration submission endpoint is invoked, **Then** the system validates all parameters, provisions the simulation run, registers the tables with identical initial shoes, and returns a 201 Created response containing the session identifier and effective configuration snapshot.
2. **Given** a client submits an invalid configuration (e.g., min bet $50 exceeding max bet $25, deck penetration 150%, or negative initial bankroll), **When** submitted, **Then** the system rejects the request with a 422 Unprocessable Entity error detailing the specific rule constraint violations without creating any simulation state.
3. **Given** a configuration omitting optional rule fields, **When** submitted, **Then** the system applies standardized casino defaults (6 decks, 75% penetration, S17, 3:2 blackjack payout, Late Surrender, American Peek, DAS enabled, $10 min bet, $500 max bet, $1,000 bankroll) and returns the fully resolved configuration.

---

### User Story 2 - Real-Time Multi-Agent Simulation Streaming & Strategy Deviation Analytics (Priority: P1)

As an analyst monitoring an active simulation from the frontend, I want to receive a live, synchronized stream of simulation events—including initial card deals, player bet sizing, hand actions (Hit, Stand, Double, Split, Surrender), dealer resolution, and bankroll adjustments across Jev, Laya, and Basic Strategy—accompanied by every model's confidence, probability distribution, latency, and real-time comparative metrics showing exactly how and why AI players deviate from Basic Strategy, so that I can observe, quantify, and visually compare AI agent decision deviations in real time.

**Why this priority**: The primary analytical purpose of the platform is comparative evaluation of AI decision models against mathematical game theory. Live turn-by-turn transparency and real-time deviation statistics are essential for user engagement and immediate insight.

**Independent Test**: Can be verified by starting a simulation session, establishing a client streaming connection via WebSocket (`/ws/simulations/{session_id}`), observing live round progression across all active tables, and verifying that every decision event delivers the chosen action, model metadata, confidence score, and complete comparison payload (optimal action, actual action, decision category, optimality boolean, and strategic reasoning), as well as cumulative deviation statistics per player.

**Acceptance Scenarios**:

1. **Given** an active simulation session, **When** a client connects to the live event stream for that session, **Then** the client receives sequential, ordered events capturing round start, opening wagers, card distributions, each player's tactical decisions with full inference metadata (choice, confidence, alternatives distribution, latency, token usage), round outcomes, and updated table bankrolls.
2. **Given** simultaneous tables running for Jev, Laya, and Basic Strategy, **When** cards are dealt and decisions evaluated, **Then** events for all three tables remain synchronized per round, with no table advancing to the next round until all active tables have settled the current round.
3. **Given** a player makes a decision, **When** the decision event is broadcast, **Then** it includes an evaluation against the mathematical Basic Strategy matrix, explicitly flagging whether the decision was optimal or suboptimal along with the recommended optimal action, decision category (Hard Total, Soft Total, Pair Split, Surrender), and reasoning.
4. **Given** Jev or Laya makes a decision that deviates from Basic Strategy, **When** the decision is processed and round is settled, **Then** the system immediately updates the entity's running strategy deviation metrics (total decisions, deviation count, optimality percentage, and category breakdown) and streams these running metrics in real-time round settlement and snapshot frames.

---

### User Story 3 - Interactive Simulation Flow Control & Fault Recovery (Priority: P2)

As a researcher investigating specific game situations, I want to control simulation execution from the UI—pausing, stepping through individual turns or rounds, resuming, or stopping the run—and receive immediate notifications if an external agent encounters a transient fault (e.g., API timeout or rate limit), with the ability to trigger a retry or abort without losing accumulated metrics or bankroll state.

**Why this priority**: Long-running simulations require interactive inspection, debugging capabilities, and resilient operational controls. When external APIs fail, users must have recovery options rather than experiencing silent failures or data corruption.

**Independent Test**: Can be verified by launching a simulation, sending a Pause command, verifying that execution halts at the round/turn boundary, triggering a Single-Step command to advance exactly one round/turn, and simulating a model error to verify that the system pauses into a recoverable error state and resumes cleanly upon Retry.

**Acceptance Scenarios**:

1. **Given** a running simulation, **When** the client sends a `pause` command, **Then** the system transitions status to `PAUSED`, halts table execution cleanly at the next turn boundary, and emits a `session_paused` event.
2. **Given** a paused simulation, **When** the client sends a `step` command (round or turn), **Then** the system executes exactly one round (or turn) across all active tables, updates metrics, and returns to `PAUSED`.
3. **Given** an external AI agent fails during inference (e.g., HTTP timeout or 429), **When** the fault occurs, **Then** the system halts execution, transitions status to `PAUSED_ERROR`, retains all table state and bankrolls without loss, and notifies the client with the failure details and eligible recovery actions (`retry` or `abort`).
4. **Given** a session in `PAUSED_ERROR`, **When** the client sends a `retry` command, **Then** the system re-attempts the failed turn and, upon success, resumes the simulation loop seamlessly.

---

### User Story 4 - Granular and Comprehensive Database JSON Data Export (Priority: P2)

As a data scientist or researcher, I want to export stored simulation records from the database as structured JSON files—either exporting a single simulation run or the entire database archive—so that I can perform offline statistical modeling, generate custom visualizations, and archive experimental results.

**Why this priority**: Users need direct access to persistent relational data for downstream research, reproducibility audits, and reporting. Granular export (single simulation vs full database) meets both targeted and archival use cases.

**Independent Test**: Can be verified by completing one or more simulation runs, requesting a JSON export for a specific `run_id` or `session_id` and confirming it downloads a valid JSON document containing the complete hierarchy (configurations, simulations, player sessions, shoes, rounds, hands, decisions, bets, and metrics), and requesting a full database export confirming it contains all stored runs.

**Acceptance Scenarios**:

1. **Given** one or more completed simulation runs in the database, **When** the client requests an export for a specific simulation run via `GET /api/export/simulations/{session_or_run_id}`, **Then** the system streams a formatted JSON file attachment containing the complete relational hierarchy for that run with HTTP headers indicating a file download.
2. **Given** a database containing multiple historical runs, **When** the client requests a full database export via `GET /api/export/database`, **Then** the system generates and streams a structured JSON file containing all historical runs, configurations, player benchmarks, and decision telemetry.
3. **Given** a request to export a non-existent simulation identifier, **When** submitted, **Then** the system returns a 404 Not Found error with a clear error description.
4. **Given** a request to export an active, running simulation, **When** submitted, **Then** the system exports a consistent point-in-time snapshot of all rounds completed up to that moment without disrupting ongoing simulation execution.

---

### User Story 5 - Historical Runs Catalog & Benchmark Analytics (Priority: P3)

As a user returning to the application, I want to browse past simulation runs, view summary benchmark metrics (net profit, win/loss/push percentages, decision optimality rates, and model latency), and retrieve round details so that I can compare performance across different configurations and models over time.

**Why this priority**: While live streaming supports real-time monitoring, historical exploration enables longitudinal analysis and performance auditing across different runs.

**Independent Test**: Can be verified by querying the runs list endpoint, confirming paginated summary records with key performance metrics per entity, and fetching detailed round results for a selected historical run.

**Acceptance Scenarios**:

1. **Given** past simulations saved in the database, **When** the client queries `GET /api/simulations`, **Then** the system returns a paginated list of runs with metadata including start time, end time, status, total rounds, table rules summary, and player performance summaries.
2. **Given** a specific past run, **When** the client queries `GET /api/simulations/{id}`, **Then** the system returns detailed run information including player session benchmarks, shoe reshuffle counts, and aggregate optimality comparisons.

---

### User Story 6 - Database Purge & Storage Reset (Priority: P3)

As a developer or researcher, I want to trigger a database reset from the frontend UI that clears all stored records across all relational tables so that I can start a fresh benchmarking suite without stale historical simulations or accumulated test data.

**Why this priority**: During active experimentation, development, or benchmark recalibration, researchers need a clean slate without having to manually drop database containers or run low-level SQL scripts.

**Independent Test**: Can be verified by running several simulations, calling the clear database endpoint, confirming a 200 OK response with the list of cleared tables, and verifying that subsequent queries to the runs, rounds, and decisions tables return an empty collection.

**Acceptance Scenarios**:

1. **Given** a database containing multiple historical runs and related records, **When** the client submits a request to `DELETE /api/database` (or `POST /api/database/clear`), **Then** the system purges all records across all relational tables in cascading order and returns a 200 OK status confirming zero remaining records.
2. **Given** a simulation currently in progress (status `RUNNING` or `PAUSED`), **When** the client requests a database clear, **Then** the system rejects the operation with a 409 Conflict error specifying that active simulations must be stopped before purging storage.

---

### Edge Cases

- **Client Disconnection During Active Simulation**: When a frontend client disconnects or reloads the browser, the backend simulation continues running in the background; when the client reconnects with the session identifier, the system resumes streaming from the current round and provides cumulative metrics.
- **Multiple Concurrent Web Clients**: Multiple clients subscribing to the same simulation session receive identical, synchronized event streams.
- **High-Speed Simulation Saturation**: When running rapid simulations (e.g., 500+ rounds/minute), event streaming must support event batching or throttling to prevent frontend message queue saturation while guaranteeing persistence integrity.
- **All Players Bankrupt**: When all participating players reach zero or below-minimum bankroll, the system gracefully terminates the simulation with status `COMPLETED_BANKRUPT`, emits final summary events, and finalizes database records.
- **Malformed Table Rules Combinations**: Rule combinations that contradict each other (e.g., `surrender_rule = EARLY` with European No Hole Card, or `hit_split_aces = True` with `resplit_aces = False`) are validated against casino rule dependency constraints with informative error messages.
- **Large Dataset Export Memory Limits**: Full database export for high-volume datasets (tens of thousands of rounds) must be streamed incrementally (chunked transfer) rather than buffered entirely in memory to prevent process memory exhaustion.
- **Unreachable AI Entity at Launch**: If a requested AI agent (e.g., Laya or Jev) fails its pre-flight connection check and `mock_mode` is False, the initialization endpoint rejects the request with HTTP 422 indicating which specific entity failed and proposing running with available entities or enabling `mock_mode`.
- **Database Clear During Active Simulation**: When a client requests a database purge while any simulation is actively running or paused, the request is rejected with HTTP 409 Conflict to protect active in-memory state and avoid partial or corrupted storage.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Configuration & Initialization
- **FR-001**: The system MUST provide an endpoint to submit a simulation configuration payload specifying round limits (`max_rounds`), number of simulations (`num_simulations`), execution mode (`visualized` vs `fast_batch`), optional pacing delay between rounds (`delay_ms`), optional random seed (`seed`), participating player subset (`entities`: any combination of `optimal`, `jev`, `laya`), optional `mock_mode` flag for offline testing, and customizable table rules.
- **FR-002**: The system MUST validate and support all customizable table rules defined in the blackjack rules specification:
  - **Dealer & Table**:
    - `soft_17_rule`: Stand on Soft 17 (`S17`) vs Hit on Soft 17 (`H17`).
    - `blackjack_payout`: Natural Blackjack payout ratio (3:2 / 1.5x, 6:5 / 1.2x, 1:1 / 1.0x).
    - `hole_card_rule`: American Style Peek vs European No Hole Card (`ENHC`).
    - `insurance_allowed`: Enable or disable insurance offers (2:1 payout).
    - `surrender_rule`: No Surrender, Early Surrender, or Late Surrender.
  - **Player Actions (Double & Split)**:
    - `double_after_split` (DAS): Allow or disallow doubling down on split hands.
    - `max_split_hands`: Maximum allowed split hands per initial pair (up to 4).
    - `resplit_aces` (RSA): Allow or disallow re-splitting pairs of Aces.
    - `hit_split_aces`: Restrict split Aces to one card only vs allow additional hits.
  - **Shoe, Cards & Decks**:
    - `num_decks`: Number of standard 52-card decks in shoe (1, 2, 4, 6, 8).
    - `penetration`: Cut card depth percentage before reshuffling (0.50 to 0.85).
    - `burn_cards_count`: Number of cards discarded at shoe initialization (0 to 5).
  - **Economy & Wagering**:
    - `initial_bankroll`: Starting capital allocated to each player table ($100 to $1,000,000).
    - `min_bet`: Table minimum wager.
    - `max_bet`: Table maximum wager.
    - `stop_on_all_bankrupt`: Halt simulation early if all players are eliminated.
- **FR-003**: The system MUST perform pre-flight health validation verifying connectivity only for requested AI entities (returning detailed diagnostics if an entity is unreachable unless `mock_mode` is enabled), and instantiate independent, isolated game tables for all active decision entities guaranteed to share identical initial shoe card sequences derived from the configured seed.
- **FR-004**: The system MUST return an initial simulation descriptor upon successful initialization containing unique session identifiers, run identifiers, effective table rules, and initial player bankrolls.

#### Simulation Execution & Real-Time Telemetry
- **FR-005**: The system MUST provide an execution trigger to launch the configured simulation asynchronously in the background.
- **FR-006**: The system MUST broadcast real-time simulation events over a persistent, bidirectional WebSocket connection (`/ws/simulations/{session_id}`) accessible to frontend clients. In `visualized` mode, events include turn-by-turn and round-by-round card deals and decisions with configurable pacing delay; in `fast_batch` mode, events report simulation completion milestones, progress percentages, and aggregate comparative analytics.
- **FR-007**: Every decision event broadcast MUST include full decision transparency and strategy comparison:
  - Participating entity identifier (`jev`, `laya`, `optimal`).
  - Chosen actual action (`hit`, `stand`, `double`, `split`, `surrender`, bet amount, insurance decision).
  - Decision context (current player hand cards and total, dealer visible upcard, shoe true count / running count if applicable).
  - Model inference telemetry (model name, confidence score, full probability distribution over legal alternatives, response latency in milliseconds, token usage).
  - Basic Strategy comparison oracle payload (`comparison`): optimality flag (`is_optimal`), recommended optimal action (`optimal_action`), decision category (`HARD_TOTAL`, `SOFT_TOTAL`, `PAIR_SPLIT`, `SURRENDER`, `INSURANCE`), legal validity flag (`is_legal`), and strategic reasoning explaining the difference.
- **FR-008**: The system MUST maintain turn-level and round-level synchronization across all active tables, ensuring no table advances until all participating entities complete their actions for that round.
- **FR-009**: The system MUST publish round summary events including dealer final hand, per-player outcomes (`win`, `loss`, `push`, `natural_blackjack`, `busted`), payout settlements, and updated cumulative bankrolls.

#### Interactive Flow Control & Error Recovery
- **FR-010**: The system MUST accept interactive flow control commands (`pause`, `resume`, `step`, `retry`, `stop`, `set_speed`) directly over the established WebSocket channel (with mirrored REST endpoints available for programmatic/headless control), allowing clients to dynamically adjust round pacing delay (0 ms unthrottled up to 2,000 ms) without interrupting execution.
- **FR-011**: When a pause command is received, execution MUST halt at the immediate round or turn boundary without losing partial hand or table state.
- **FR-012**: In the event of an external agent failure (such as TypeSafe Jev or Laya network timeout or HTTP 429 rate limit), the system MUST automatically transition to a paused error state (`PAUSED_ERROR`), preserve all accumulated simulation state, emit an error alert event to the frontend, and expose endpoints to `retry` the failed entity or `abort` the simulation.

#### Data Persistence & JSON Export
- **FR-013**: The system MUST automatically persist all simulation runs, configurations, rounds, hands, decisions, bets, and telemetry events into the relational database.
- **FR-014**: The system MUST provide an export endpoint (`/api/export/simulations/{id}`) that serializes the complete hierarchical document of a specified simulation run (matching the `RunExporter` schema) into a downloadable JSON file.
- **FR-015**: The single-simulation hierarchical JSON export MUST include:
  - Run metadata (id, timestamp, duration, status, seed).
  - Full configuration parameters and table rules.
  - Participating entity descriptors and final metrics (net profit, win/loss/push counts, blackjacks, optimality percentage).
  - Complete round-by-round history: shoe generations, dealt card sequences, player wagers, tactical decisions with inference metadata, dealer hand outcomes, and bankroll transitions.
- **FR-016**: The system MUST provide a full database export endpoint (`/api/export/database`) that serializes all historical simulation runs as an array of hierarchical run documents alongside global aggregate benchmarks into a comprehensive JSON archive.
- **FR-017**: All JSON export endpoints MUST serve responses with appropriate file download headers (`Content-Disposition: attachment; filename="..."`) and support streamed serialization for datasets exceeding 50 MB to prevent server memory bloat.

#### Historical Query & Performance Analytics
- **FR-018**: The system MUST provide endpoints to query past simulation runs with pagination, filtering by date, status, or entity type, and summary statistics.
- **FR-019**: The system MUST provide an endpoint to fetch detailed metrics and round replays for any completed historical simulation run.

#### Database Maintenance & State Purge
- **FR-020**: The system MUST provide an endpoint (`DELETE /api/database` or `POST /api/database/clear`) to purge all stored records across all database tables (runs, configurations, simulations, player sessions, shoes, rounds, round players, hands, card events, bets, transactions, decisions, and model responses).
- **FR-021**: The database purge operation MUST prevent execution if an active simulation is currently running or paused (returning HTTP 409 Conflict), protecting active memory state from inconsistent storage.
- **FR-022**: Upon successful purge, the database endpoint MUST return a summary of cleared tables and reset counts, leaving the database schema fully intact and immediately available for new simulation runs.

#### Strategy Deviation Analytics
- **FR-023**: The system MUST compute and maintain running strategy deviation statistics for each active entity across the simulation session:
  - Overall decision totals: total decisions evaluated, total deviations (suboptimal decisions), and overall optimality rate (percentage).
  - Category-level breakdown: decision counts, deviation counts, and optimality percentages segmented by `hard_totals`, `soft_totals`, `pair_splits`, and `surrenders`.
  - Wagering / Bet spread deviations: total wagers evaluated, count of suboptimal bets against the optimal Hi-Lo spread, cumulative absolute bet delta ($), and average bet deviation per round.
  - These running statistics MUST be included in `ROUND_SETTLED`, `SESSION_SNAPSHOT`, and `SESSION_COMPLETED` WebSocket frames.
- **FR-024**: The system MUST provide an endpoint (`GET /api/simulations/{session_id}/deviations`) that returns the current cumulative and category-segmented strategy deviation analytics for all participating entities in the specified simulation session.

---

### Key Entities *(include if feature involves data)*

- **SimulationRunConfig**: Configuration payload representing user parameters:
  - `session_id`, `seed`, `max_rounds`, `num_simulations`, `initial_bankroll`.
  - `entities`: List of active player types (`jev`, `laya`, `optimal`).
  - `table_rules`: Nested structure capturing dealer rules, player action permissions, shoe parameters, and wagering boundaries.
- **SimulationSession**: Active runtime state of an orchestrated simulation:
  - `session_id`, `run_id`, `status` (`INITIALIZING`, `RUNNING`, `PAUSED`, `PAUSED_ERROR`, `COMPLETED`, `STOPPED`).
  - `current_round`, `max_rounds`, `seed`, `start_time`, `end_time`.
  - `tables`: Map of entity identifiers to their isolated table states, current bankrolls, active hands, and shoe counters.
  - `metrics`: Per-entity performance metrics (rounds played, net profit, wins, losses, pushes, blackjacks, optimality score).
- **DecisionTelemetryRecord**: Complete payload of a single player decision event:
  - `round_number`, `entity_id`, `hand_id`, `action`.
  - `confidence`, `probabilities`, `latency_ms`, `input_tokens`, `output_tokens`.
  - `comparison`: `is_optimal`, `optimal_action`, `category`, `reasoning`, `is_legal`.
- **EntityDeviationStats**: Real-time aggregated comparative analytics for a player against Basic Strategy:
  - `entity_id`, `total_decisions`, `optimal_decisions`, `deviations_count`, `optimality_percentage`.
  - `categories`: Map of decision categories (`hard_total`, `soft_total`, `pair_split`, `surrender`, `insurance`) to their respective counts, deviations, and accuracy rates.
  - `betting_deviations`: Wager count, suboptimal wagers, total absolute bet delta, and average bet discrepancy.
- **ExportArchive**: Structured JSON representation of simulation data:
  - Single simulation export: Contains root run metadata, rules, players, and full round-by-round sequence.
  - Full database export: Contains an array of all run archives with global aggregate benchmarks and database schema revision info.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can configure, customize all table rules, and launch a multi-agent simulation from the frontend in under 30 seconds.
- **SC-002**: Real-time decision telemetry is delivered to connected clients with a transport dispatch latency of less than 150 ms following decision generation.
- **SC-003**: 100% of decisions made by Jev, Laya, and Basic Strategy are broadcast with complete metadata (action, confidence, probabilities, latency, optimality flag) and zero dropped decision events.
- **SC-004**: Flow control commands (`pause`, `resume`, `step`, `stop`) take effect within 1 round boundary (less than 500 ms for active turns).
- **SC-005**: Single simulation JSON export downloads successfully in under 3 seconds for simulations up to 1,000 rounds.
- **SC-006**: Full database JSON export processes up to 50,000 historical rounds using stream serialization without exceeding 256 MB of backend memory usage.
- **SC-007**: 100% of rule permutations defined in the Blackjack rules document (S17/H17, DAS/no-DAS, RSA, Surrender styles, 1-8 decks, peek/ENHC) are validated and respected during simulation execution.
- **SC-008**: Strategy deviation statistics (optimality percentage, category breakdowns, and bet spread deltas) are updated and streamed in real time with 100% mathematical accuracy against the Basic Strategy oracle, and queryable via REST with sub-50ms response time.

---

## Assumptions

- The frontend application will connect over standard HTTP and WebSocket protocols to the backend service running locally or in Docker on `localhost:8000`.
- The existing persistence layer and `RunExporter` in `backend/app/persistence/` provide the foundational database models and single-run JSON serialization logic, which this feature expands with REST endpoints, streaming export, full-database export, and configuration endpoints.
- If an external agent service (such as remote TypeSafe API or local Laya service) is unavailable at simulation start, the system permits running simulations with available subsets of players (e.g. Optimal Strategy alone, or Optimal + whichever AI agent is active).
- Exported JSON files use UTF-8 encoding and standard ISO-8601 timestamps.
- Default configuration values align with standard Las Vegas Strip / Atlantic City rules (6 decks, 75% penetration, S17, 3:2 payout, late surrender, DAS, American Peek) when specific rules are not provided by the user.
