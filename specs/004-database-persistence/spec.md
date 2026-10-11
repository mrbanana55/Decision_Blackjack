# Feature Specification: Database Schema & Simulation Telemetry Persistence

**Feature Branch**: `004-database-persistence`

**Created**: 2026-10-11

**Status**: Draft

**Input**: User description: "Let's create the database for the project. You may take a look at docs/Diseño Base de Datos (Modelo ER).md to get an idea of what the database should have"

## Clarifications

### Session 2026-10-11
- Q: How should the simulation orchestrator dispatch telemetry events to the database persistence layer during active simulation runs? (FR-011) → A: Asynchronous Event Subscriber (Option A): A database persistence listener subscribes to the orchestrator's event stream via `EventEmitter`, buffering and persisting records asynchronously without coupling engine or table execution loops to database calls.
- Q: How should database schema provisioning and migrations be managed across development, testing, and production environments? (FR-015) → A: Auto-Provision with Migration Scripts (Option A): Schema automatically creates missing tables on test/service startup if not present, while also providing standalone migration scripts for controlled production deployment.
- Q: What batch flush trigger policy should the persistence service use to balance memory usage, transaction throughput, and data safety during high-volume simulations? (FR-012) → A: Atomic Round-Boundary Flush (Option A): Buffer intermediate turn and card events in memory and commit them in atomic transactions at round conclusion, or in configurable batches of $N$ completed rounds for high-speed runs, ensuring zero partial round states on pause or failure.
- Q: How should the database abstraction support local automated testing when an external PostgreSQL server is not running? (FR-015) → A: Strict PostgreSQL Dependency (Option B): All database schema definitions, queries, and integration tests exclusively target PostgreSQL (utilizing native JSONB, UUID, and ENUM types). In local testing environments without an active PostgreSQL instance, database-dependent tests skip gracefully with a clear setup notice.
- Q: What deletion and data lifecycle policy should the database enforce when a simulation Run is deleted? (FR-002) → A: Hard Cascading Deletion (Option A): Deleting a Run executes a database-level cascading deletion (`ON DELETE CASCADE`) across foreign keys, cleanly removing all associated child simulations, shoes, rounds, hands, card events, decisions, and transactions without leaving orphaned rows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Relational Database Schema & Domain Entity Integrity (Priority: P1) 🎯 MVP

As a simulation researcher or data analyst, I want a complete, strongly-typed relational database schema reflecting the 15 domain entities defined in `docs/Diseño Base de Datos (Modelo ER).md`, so that every simulation run, participant session, card deal, AI model inference, decision, wager, and bankroll transition is modeled with strict relational integrity.

**Why this priority**: Foundational core of the database layer. Without the proper schema, tables, foreign keys, uniqueness constraints, and indexes, neither orchestrator telemetry nor historical analysis can function safely.

**Independent Test**: Can be tested independently by applying schema migrations to an isolated relational database instance, verifying table definitions, data types, constraints (e.g., unique session shoes, unique round numbers per simulation), and validating referential cascade rules with synthetic domain records.

**Acceptance Scenarios**:

1. **Given** a clean relational database, **When** the schema initialization is executed, **Then** all 15 entities (`RUN`, `RUN_CONFIGURATION`, `SIMULATION`, `PLAYER_SESSION`, `SHOE`, `PLAYER_SHOE_STATE`, `ROUND`, `ROUND_PLAYER`, `HAND`, `CARD_EVENT`, `BET`, `DECISION`, `MODEL_RESPONSE`, `HAND_RESULT`, `BANKROLL_TRANSACTION`) and their corresponding enumerations are created without error.
2. **Given** a simulation with three participant entities (Jev, Laya, Optimal), **When** creating player sessions, **Then** the database enforces uniqueness on `(simulation_id, player_type)`, preventing duplicate sessions for the same player type within a single simulation.
3. **Given** a round in a simulation, **When** persisting round players, **Then** the database enforces uniqueness on `(round_id, player_session_id)`, and `bankroll_before`/`bankroll_after` record the financial state for that participant in that specific round.
4. **Given** split hands originating from an initial hand, **When** persisting split child hands, **Then** each child hand references its `parent_hand_id`, correctly representing arbitrary split and resplit hierarchies.
5. **Given** player and dealer cards dealt across rounds, **When** inserting card records into `CARD_EVENT`, **Then** the database records sequence number, shoe position, shoe reference, recipient (Dealer vs Hand), and card identity (`e.g., "AS", "10H"`).

---

### User Story 2 - Real-Time Orchestrator Event Ingestion & Audit Logging (Priority: P1)

As a simulation orchestrator, I want an asynchronous persistence service that consumes live simulation events (shoe generation, card deals, player decisions, model responses, hand results, and bankroll ledger entries) and writes them to the database without blocking or slowing down core blackjack engine mechanics, so that simulation progress is safely stored in real-time.

**Why this priority**: Required for live experiment monitoring and telemetry capture. The database must serve as a structured persistent recorder, strictly decoupled from the core rule evaluation engine as mandated by Constitution Principle V.

**Independent Test**: Can be tested independently by publishing an end-to-end multi-round orchestrator event stream through the persistence service and verifying that all database records match the event stream exactly, with correct foreign key linkages and timestamps.

**Acceptance Scenarios**:

1. **Given** an orchestrated simulation round executing turns for Jev, Laya, and Optimal, **When** a player decision event is emitted, **Then** the persistence layer records the `DECISION` entity containing `action`, `confidence_pct`, `running_count`, `true_count`, `bankroll_at_decision`, `state_snapshot`, `optimal_reference_action`, and `agrees_with_optimal`.
2. **Given** an external AI agent (Jev or Laya) returning an inference response, **When** the response event is processed, **Then** the persistence layer records the `MODEL_RESPONSE` entity linked to the decision, storing `provider`, `model_name`, `model_version`, `request_payload`, `response_payload`, `http_status`, `latency_ms`, and error fields.
3. **Given** an opening wager, double down, split bet, insurance bet, or round payout, **When** financial events occur, **Then** the persistence layer writes records to both `BET` and `BANKROLL_TRANSACTION`, maintaining an immutable ledger where `balance_after = balance_before + amount`.
4. **Given** multiple players sharing the same shoe permutation, **When** each player consumes cards at their own pace, **Then** the persistence layer updates `PLAYER_SHOE_STATE` with `current_position`, `cards_seen`, `running_count`, and `true_count` without duplicating the underlying shoe card sequence.

---

### User Story 3 - High-Volume Batch Persistence & Structured Run Export (Priority: P2)

As an experiment runner executing large-scale simulations (e.g., 10,000+ rounds), I want the persistence layer to buffer event records in memory and commit them in configurable batch transactions, and support exporting completed runs into structured file artifacts (`/data/runs/[timestamp]`), so that high-throughput runs avoid buffer bloat, memory exhaustion, or database connection saturation.

**Why this priority**: Mandated by Constitution Principle V for high-volume simulations exceeding 10,000 rounds and reproducible archival export.

**Independent Test**: Can be tested independently by running a simulated 10,000-round workload with batch persistence enabled, verifying memory utilization remains stable under a defined threshold, and confirming that the exported JSON artifact reproduces the full run structure.

**Acceptance Scenarios**:

1. **Given** a simulation running with batch persistence enabled (e.g., batch size of 500 rounds or 1,000 events), **When** high-speed round execution proceeds, **Then** records are buffered and flushed to the database in transactional batches, maintaining database write latency under 200 ms per batch.
2. **Given** a simulation completing or reaching termination, **When** the export command is triggered, **Then** the persistence service exports a complete, self-contained JSON file artifact to `/data/runs/[timestamp]/run_data.json` containing the full run hierarchy (run configuration, simulations, player sessions, round summaries, and performance telemetry).
3. **Given** an unexpected simulation crash or interruption during a batch run, **When** the orchestrator halts, **Then** all uncommitted buffered events are gracefully flushed or cleanly aborted to prevent partial/corrupted round records, and the `RUN` record is marked with status `ERROR` and descriptive error message.

---

### User Story 4 - Historical Simulation Querying & Analytical Replay (Priority: P2)

As a researcher comparing decision models against game theory, I want structured query repositories to retrieve run histories, round-by-round replay timelines, model latency distributions, bankroll trajectories, and basic strategy agreement rates, so that downstream analytical dashboards and reporting tools can evaluate model performance without re-computing raw game mechanics.

**Why this priority**: The primary business goal of Decision_Blackjack is comparative benchmarking between AI decision models (Jev, Laya) and Optimal Strategy. The database must make analytical metrics straightforward to query.

**Independent Test**: Can be tested independently by querying a persisted simulation run with known outcomes, verifying that computed metrics (win rate, loss rate, push rate, ROI, optimal agreement percentage) match the exact game events without storing redundant, stale derived columns.

**Acceptance Scenarios**:

1. **Given** a completed simulation run with Jev, Laya, and Optimal, **When** querying the player comparison summary, **Then** the repository returns the final bankroll, net profit/loss, total bets placed, win/loss/push counts, and optimal decision agreement percentage for each player session.
2. **Given** a specific round ID, **When** requesting a round replay timeline, **Then** the repository returns the full sequence of dealer cards, player hands, decision points (with state snapshots and AI latencies), and resulting bankroll transactions ordered chronologically by `sequence_number`.
3. **Given** an external AI agent evaluation, **When** querying model performance metrics, **Then** the repository returns inference latency percentiles (p50, p95, p99), HTTP status breakdown, and agreement percentage partitioned by decision type (Hard total, Soft total, Pair split).

---

### Edge Cases

- **Simulation Pause or Sudden Abort**: When an external model fails (e.g., HTTP 5xx or timeout), the active run status transitions to `PAUSED` or `ERROR`. In-flight hand events must be committed up to the last valid action, with error telemetry preserved in `MODEL_RESPONSE` and `RUN.error_message`.
- **Complex Split and Resplit Hierarchies**: When a player splits Aces or resplits pairs up to the table limit (e.g., 4 hands), each hand must be uniquely identified, linked to its parent hand via `parent_hand_id`, and associated with its specific wagers and final outcomes.
- **Natural Blackjack Immediate Resolution (American Peek)**: When the dealer has natural blackjack, player hands resolve immediately without player decision turns; the database must record the round, dealer cards, and immediate bankroll settlements with zero `DECISION` entries for players who did not get a turn.
- **Surrender & Insurance Settlements**: Surrender causes a 50% bet return and early hand termination; insurance creates a side bet resolved against dealer blackjack. Both must create distinct `BET` records and corresponding `BANKROLL_TRANSACTION` entries with proper signed amounts (negative for stake, positive for win/refund).
- **Shoe Exhaustion & Mid-Round Reshuffle**: When a shoe reaches its penetration threshold, the current round finishes with the current shoe. The subsequent round triggers a new `SHOE` record, and all three `PLAYER_SHOE_STATE` records are updated or reset accordingly.
- **Divergent Table Progress**: Because Jev, Laya, and Optimal may hit or stand differently, their card consumption from the shared shoe diverges. The database tracks distinct `PLAYER_SHOE_STATE.current_position` values per session, guaranteeing that each player's shoe consumption is accurately audited.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define and manage all 15 relational entities specified in `docs/Diseño Base de Datos (Modelo ER).md`:
  1. `RUN`: Top-level experiment execution record (`id`, `status`, `created_at`, `started_at`, `finished_at`, `error_message`, `data_directory`).
  2. `RUN_CONFIGURATION`: Immutable parameter snapshot (`soft_17_rule`, `blackjack_payout_ratio`, `split_aces_blackjack_rule`, `hole_card_rule`, `insurance_enabled`, `insurance_payout_ratio`, `surrender_rule`, `das_enabled`, `max_resplit`, `rsa_enabled`, `hit_split_aces`, `charlie_rule`, `number_of_decks`, `penetration`, `burn_cards`, `initial_bankroll`, `minimum_bet`, `maximum_bet`, `rounds_per_simulation`, `rounds_indefinite`, `simulations_count`, `simulations_indefinite`, `user_seed`, `optimal_bet_spread`).
  3. `SIMULATION`: Individual simulation instance within a run (`simulation_number`, `seed`, `status`, `initial_bankroll`, `final_bankroll`, `termination_reason`, `started_at`, `finished_at`).
  4. `PLAYER_SESSION`: Participant session tracking (`player_type`, `initial_bankroll`, `current_bankroll`, `status`).
  5. `SHOE`: Shared card shoe generated per simulation (`shoe_number`, `seed`, `card_order`, `total_cards`, `burn_cards`, `penetration`, `generated_by_session_id`, `created_at`).
  6. `PLAYER_SHOE_STATE`: Independent card consumption and counting tracker per player per shoe (`current_position`, `cards_seen`, `running_count`, `true_count`, `started_at`, `finished_at`).
  7. `ROUND`: Common round execution container (`round_number`, `status`, `dealer_final_value`, `dealer_blackjack`, `dealer_bust`, `started_at`, `finished_at`).
  8. `ROUND_PLAYER`: Player participation and financial balance in a round (`bankroll_before`, `bankroll_after`, `status`, `started_at`, `finished_at`).
  9. `HAND`: Individual hand instance, supporting split trees (`hand_number`, `parent_hand_id`, `is_initial`, `is_split`, `status`, `final_value`, `is_blackjack`, `is_bust`).
  10. `CARD_EVENT`: Ordered chronicle of every card dealt (`recipient`, `event_type`, `card`, `sequence_number`, `shoe_position`, `shoe_id`, `hand_id`, `created_at`).
  11. `BET`: Specific financial commitment (`bet_type`, `amount`, `created_at`).
  12. `DECISION`: Granular player move record (`decision_number`, `decision_type`, `action`, `confidence_pct`, `running_count`, `true_count`, `bankroll_at_decision`, `optimal_reference_action`, `agrees_with_optimal`, `state_snapshot`, `created_at`).
  13. `MODEL_RESPONSE`: Complete AI inference record (`provider`, `model_name`, `model_version`, `request_payload`, `response_payload`, `http_status`, `latency_ms`, `error_type`, `error_message`, `requested_at`, `responded_at`).
  14. `HAND_RESULT`: Final outcome per hand (`result`, `player_value`, `dealer_value`, `payout_amount`, `net_amount`, `created_at`).
  15. `BANKROLL_TRANSACTION`: Immutable double-entry style ledger entry (`transaction_type`, `amount`, `balance_before`, `balance_after`, `created_at`).
- **FR-002**: System MUST enforce relational integrity via foreign keys with `ON DELETE CASCADE` across the entire hierarchy (`RUN` $\rightarrow$ `RUN_CONFIGURATION`, `SIMULATION` $\rightarrow$ `PLAYER_SESSION`, `SHOE`, `ROUND` $\rightarrow$ `HAND`, `CARD_EVENT`, `DECISION`, `BET`, `BANKROLL_TRANSACTION`), ensuring that deleting a `RUN` completely purges all associated child records without leaving orphaned rows, alongside explicit unique constraints:
  - `SIMULATION`: Unique on `(run_id, simulation_number)`.
  - `PLAYER_SESSION`: Unique on `(simulation_id, player_type)`.
  - `SHOE`: Unique on `(simulation_id, shoe_number)`.
  - `PLAYER_SHOE_STATE`: Unique on `(player_session_id, shoe_id)`.
  - `ROUND`: Unique on `(simulation_id, round_number)`.
  - `ROUND_PLAYER`: Unique on `(round_id, player_session_id)`.
- **FR-003**: System MUST NOT store sensitive credentials or API keys anywhere within the database schema or exported files.
- **FR-004**: System MUST maintain database indexes on primary query pathways:
  - `SIMULATION(run_id)`
  - `PLAYER_SESSION(simulation_id, player_type)`
  - `SHOE(simulation_id, shoe_number)`
  - `PLAYER_SHOE_STATE(player_session_id, shoe_id)`
  - `ROUND(simulation_id, round_number)`
  - `ROUND_PLAYER(round_id, player_session_id)`
  - `HAND(round_player_id)`
  - `CARD_EVENT(round_id, sequence_number)`
  - `CARD_EVENT(shoe_id, shoe_position)`
  - `DECISION(hand_id, decision_number)`
  - `MODEL_RESPONSE(decision_id)`
  - `BET(round_player_id)`
  - `BANKROLL_TRANSACTION(round_player_id, created_at)`
- **FR-005**: System MUST operate strictly as a persistent record store and MUST NOT execute, validate, or mutate core blackjack game rules inside the database.
- **FR-006**: System MUST record the exact positional `optimal_reference_action` and `agrees_with_optimal` boolean directly inside the `DECISION` entity for external models (Jev, Laya) based on their specific table state.
- **FR-007**: System MUST record the full JSON request and response payloads, model metadata, and round-trip inference latency in `MODEL_RESPONSE` for auditing and performance analysis.
- **FR-008**: System MUST record `state_snapshot` in `DECISION` containing the exact hand cards, dealer upcard, running count, true count, and bankroll at the moment of decision.
- **FR-009**: System MUST record signed amounts in `BANKROLL_TRANSACTION` (`amount < 0` for money leaving bankroll such as wagers, `amount > 0` for money returning such as payouts and refunds) ensuring `balance_after == balance_before + amount`.
- **FR-010**: System MUST NOT persist redundant, calculated statistical summaries (win rate, loss rate, ROI, agreement %) as permanent table columns; these MUST be computed dynamically via analytical queries or views.
- **FR-011**: System MUST provide an asynchronous telemetry persistence listener subscribing to the orchestrator's `EventEmitter` stream that buffers and writes events to the database without synchronous blocking or mutating engine execution loops.
- **FR-012**: System MUST implement an atomic round-boundary batch flush policy: buffering intermediate events during turns and committing them in atomic transactions at round conclusion, or in configurable batches of $N$ completed rounds for high-volume simulations, ensuring zero partial round states on pause or failure.
- **FR-013**: System MUST support exporting completed run data to a structured JSON artifact stored in `/data/runs/[timestamp]/run_data.json`.
- **FR-014**: System MUST provide repository query methods to retrieve run metadata, round replay histories, player session summaries, and model benchmark comparisons.
- **FR-015**: System MUST support automatic schema provisioning on test and local service startup if tables do not exist, while providing standalone migration scripts for reproducible production deployment and schema upgrades.

### Key Entities

- **Run & Configuration (`RUN`, `RUN_CONFIGURATION`)**: Represents a top-level benchmark experiment execution and its immutable rule and hyperparameter snapshot (table rules, seed, bankrolls, betting limits, deck penetration).
- **Simulation (`SIMULATION`)**: A single repetition within a Run, carrying its own deterministic seed and initial bankroll.
- **Participant Session (`PLAYER_SESSION`)**: Represents one of the three decision entities (`JEV`, `LAYA`, `OPTIMAL`) throughout a simulation, tracking its cumulative bankroll and status.
- **Shoe & Consumption State (`SHOE`, `PLAYER_SHOE_STATE`)**: The shared multi-deck card shoe produced for a simulation, alongside each player's individual consumption tracking (position index, cards seen, running count, true count).
- **Round & Round Player (`ROUND`, `ROUND_PLAYER`)**: The shared round container and each participant's individual financial stake and status within that round.
- **Hand (`HAND`)**: A blackjack hand owned by a round player, supporting recursive tree relationships (`parent_hand_id`) for split and resplit scenarios.
- **Card Deal Chronicle (`CARD_EVENT`)**: An ordered record of every card drawn from a shoe and dealt to a hand or dealer up/hole card.
- **Wager (`BET`)**: Monetary stakes placed during a round (Initial, Double, Split, Insurance).
- **Decision & Model Audit (`DECISION`, `MODEL_RESPONSE`)**: The action taken by a player on a hand, paired with the optimal strategy baseline for that exact state and the complete raw AI provider telemetry.
- **Hand Result (`HAND_RESULT`)**: The terminal outcome of a hand (Win, Loss, Push, Blackjack, Bust, Surrender) with net payout.
- **Bankroll Ledger (`BANKROLL_TRANSACTION`)**: Double-entry financial audit record tracking balance changes across bets and payouts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the 15 domain entities defined in `docs/Diseño Base de Datos (Modelo ER).md` are implemented with complete constraint and index definitions.
- **SC-002**: Database ingestion overhead adds less than 15 ms of latency per individual round event under standard simulation execution.
- **SC-003**: In batch persistence mode, the persistence worker handles a continuous simulation workload of 10,000 rounds without exceeding 256 MB of process RAM growth.
- **SC-004**: Full round replay query retrieves a complete 3-player round timeline (including all cards, decisions, model responses, and ledger entries) in under 50 ms.
- **SC-005**: 100% of persisted transactions obey the ledger invariant: `balance_after == balance_before + amount`.
- **SC-006**: Run export generates a valid, fully parseable JSON file conforming to the run schema within 2 seconds for a 1,000-round simulation.

## Assumptions

- **Target Database**: Exclusively PostgreSQL 15+ utilizing native UUID, JSONB, TIMESTAMPTZ, and enum types without multi-dialect translation layers.
- **Test Environment & Skipping**: Database integration tests connect to a live PostgreSQL instance (configured via `DATABASE_URL` or standard localhost container). In local environments without a running PostgreSQL server, database-dependent integration tests skip gracefully with an informative setup notice.
- **Engine Independence**: The blackjack engine remains completely unaware of database drivers or SQL; communication happens purely via decoupled events, repositories, or an event-subscriber bridge.
- **Storage Location**: Run file artifacts and raw export dumps are written to `/data/runs/[timestamp]` relative to the workspace root or configured data directory.
- **Timestamp Standardization**: All timestamps stored in the database are UTC with timezone awareness (ISO 8601).
- **Monetary Precision**: Bankroll amounts, wagers, and payouts use decimal/numeric types with fixed 2-decimal place precision to prevent floating-point rounding errors.
