# Data Model: Database Schema & Telemetry Persistence

**Feature**: `specs/004-database-persistence` | **Date**: 2026-10-11

This document specifies the relational data model for the Decision_Blackjack persistence layer, based on [`docs/Diseño Base de Datos (Modelo ER).md`](../../docs/Diseño%20Base%20de%20Datos%20(Modelo%20ER).md) and implemented via SQLAlchemy 2.0 AsyncIO with PostgreSQL 16.

---

## 1. Domain Groupings & Relational Architecture

The 15 entities are organized into 6 functional domains:

```text
1. Execution:     RUN, RUN_CONFIGURATION, SIMULATION
2. Participants:  PLAYER_SESSION
3. Shoes:         SHOE, PLAYER_SHOE_STATE
4. Game Flow:     ROUND, ROUND_PLAYER, HAND, CARD_EVENT
5. Decisions/AI:  DECISION, MODEL_RESPONSE
6. Economy:       BET, HAND_RESULT, BANKROLL_TRANSACTION
```

All primary keys use UUID v4. All descendant foreign keys implement `ON DELETE CASCADE`.

---

## 2. Enumeration Types (PostgreSQL ENUMs)

```sql
-- Execution & Sessions
CREATE TYPE run_status AS ENUM ('CREATED', 'RUNNING', 'PAUSE_REQUESTED', 'PAUSED', 'ERROR', 'COMPLETED', 'CANCELLED');
CREATE TYPE simulation_status AS ENUM ('RUNNING', 'COMPLETED', 'BANKRUPT', 'ERROR', 'CANCELLED');
CREATE TYPE player_type AS ENUM ('JEV', 'LAYA', 'OPTIMAL');
CREATE TYPE session_status AS ENUM ('ACTIVE', 'COMPLETED', 'BANKRUPT', 'ERROR');
CREATE TYPE termination_reason AS ENUM ('ROUNDS_COMPLETED', 'ALL_BANKRUPT', 'USER_STOPPED', 'ERROR');

-- Game Flow & Rules
CREATE TYPE round_status AS ENUM ('IN_PROGRESS', 'COMPLETED', 'ERROR');
CREATE TYPE player_round_status AS ENUM ('ACTIVE', 'RESOLVED', 'BUSTED', 'SURRENDERED', 'BLACKJACK');
CREATE TYPE hand_status AS ENUM ('IN_PLAY', 'RESOLVED', 'BUSTED', 'DOUBLED', 'SURRENDERED');
CREATE TYPE card_recipient AS ENUM ('DEALER', 'HAND');
CREATE TYPE card_event_type AS ENUM ('DEAL', 'BURN', 'REVEAL');

-- Decisions & AI
CREATE TYPE decision_type AS ENUM ('INITIAL', 'AFTER_HIT', 'AFTER_SPLIT', 'INSURANCE');
CREATE TYPE player_action AS ENUM ('HIT', 'STAND', 'DOUBLE', 'SPLIT', 'SURRENDER', 'INSURANCE_ACCEPT', 'INSURANCE_DECLINE');
CREATE TYPE model_provider AS ENUM ('SYSTEM_ONE', 'LOCAL_MODEL', 'BASIC_STRATEGY');

-- Economy
CREATE TYPE bet_type AS ENUM ('INITIAL', 'DOUBLE', 'SPLIT', 'INSURANCE');
CREATE TYPE hand_result_type AS ENUM ('WIN', 'LOSS', 'PUSH', 'BLACKJACK', 'BUST', 'SURRENDER');
CREATE TYPE transaction_type AS ENUM ('BET', 'PAYOUT', 'REFUND', 'INSURANCE', 'SURRENDER', 'ADJUSTMENT');

-- Rule Configuration
CREATE TYPE soft_17_rule AS ENUM ('STAND', 'HIT');
CREATE TYPE hole_card_rule AS ENUM ('AMERICAN_PEEK', 'ENHC');
CREATE TYPE split_aces_blackjack_rule AS ENUM ('NATURAL', 'COUNT_21');
CREATE TYPE surrender_rule AS ENUM ('NONE', 'LATE');
CREATE TYPE charlie_rule AS ENUM ('NONE', 'FIVE_CARD', 'SIX_CARD', 'SEVEN_CARD');
```

---

## 3. Entity Definitions

### 3.1 Execution Domain

#### `RUN`
Represents an entire multi-simulation experiment run.
- `id`: `UUID` (PK)
- `status`: `run_status` (NOT NULL, default: `'CREATED'`)
- `created_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- `started_at`: `TIMESTAMPTZ` (NULL)
- `finished_at`: `TIMESTAMPTZ` (NULL)
- `error_message`: `TEXT` (NULL)
- `data_directory`: `TEXT` (NULL, e.g. `"/data/runs/2026-10-11T16-00-00_uuid"`)

#### `RUN_CONFIGURATION`
Immutable snapshot of table rules and experiment parameters.
- `id`: `UUID` (PK)
- `run_id`: `UUID` (FK $\rightarrow$ `RUN.id`, ON DELETE CASCADE, UNIQUE)
- **Table Rules**:
  - `soft_17_rule`: `soft_17_rule` (NOT NULL)
  - `blackjack_payout_ratio`: `DECIMAL(5, 3)` (NOT NULL, e.g. 1.5 for 3:2, 1.2 for 6:5)
  - `split_aces_blackjack_rule`: `split_aces_blackjack_rule` (NOT NULL)
  - `hole_card_rule`: `hole_card_rule` (NOT NULL)
  - `insurance_enabled`: `BOOLEAN` (NOT NULL)
  - `insurance_payout_ratio`: `DECIMAL(5, 3)` (NOT NULL, default 2.0)
  - `surrender_rule`: `surrender_rule` (NOT NULL)
  - `das_enabled`: `BOOLEAN` (NOT NULL)
  - `max_resplit`: `SMALLINT` (NOT NULL, default 3)
  - `rsa_enabled`: `BOOLEAN` (NOT NULL)
  - `hit_split_aces`: `BOOLEAN` (NOT NULL)
  - `charlie_rule`: `charlie_rule` (NOT NULL, default `'NONE'`)
  - `number_of_decks`: `SMALLINT` (NOT NULL, default 6)
  - `penetration`: `DECIMAL(4, 3)` (NOT NULL, e.g. 0.750)
  - `burn_cards`: `SMALLINT` (NOT NULL, default 1)
  - `initial_bankroll`: `DECIMAL(12, 2)` (NOT NULL)
  - `minimum_bet`: `DECIMAL(10, 2)` (NOT NULL)
  - `maximum_bet`: `DECIMAL(10, 2)` (NOT NULL)
- **Experiment Parameters**:
  - `rounds_per_simulation`: `INTEGER` (NOT NULL)
  - `rounds_indefinite`: `BOOLEAN` (NOT NULL, default FALSE)
  - `simulations_count`: `INTEGER` (NOT NULL, default 1)
  - `simulations_indefinite`: `BOOLEAN` (NOT NULL, default FALSE)
  - `user_seed`: `BIGINT` (NULL)
  - `optimal_bet_spread`: `JSONB` (NULL)

#### `SIMULATION`
A single repetition within a Run.
- `id`: `UUID` (PK)
- `run_id`: `UUID` (FK $\rightarrow$ `RUN.id`, ON DELETE CASCADE, NOT NULL)
- `simulation_number`: `INTEGER` (NOT NULL)
- `seed`: `BIGINT` (NOT NULL)
- `status`: `simulation_status` (NOT NULL, default `'RUNNING'`)
- `initial_bankroll`: `DECIMAL(12, 2)` (NOT NULL)
- `final_bankroll`: `DECIMAL(12, 2)` (NULL)
- `termination_reason`: `termination_reason` (NULL)
- `started_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- `finished_at`: `TIMESTAMPTZ` (NULL)
- **Constraints**: `UNIQUE (run_id, simulation_number)`, `CHECK (simulation_number > 0)`

---

### 3.2 Participants Domain

#### `PLAYER_SESSION`
Tracks one decision entity (`JEV`, `LAYA`, `OPTIMAL`) throughout a simulation.
- `id`: `UUID` (PK)
- `simulation_id`: `UUID` (FK $\rightarrow$ `SIMULATION.id`, ON DELETE CASCADE, NOT NULL)
- `player_type`: `player_type` (NOT NULL)
- `initial_bankroll`: `DECIMAL(12, 2)` (NOT NULL)
- `current_bankroll`: `DECIMAL(12, 2)` (NOT NULL)
- `status`: `session_status` (NOT NULL, default `'ACTIVE'`)
- **Constraints**: `UNIQUE (simulation_id, player_type)`

---

### 3.3 Shoes Domain

#### `SHOE`
The shared card sequence for a simulation.
- `id`: `UUID` (PK)
- `simulation_id`: `UUID` (FK $\rightarrow$ `SIMULATION.id`, ON DELETE CASCADE, NOT NULL)
- `shoe_number`: `INTEGER` (NOT NULL)
- `seed`: `BIGINT` (NOT NULL)
- `card_order`: `JSONB` (NOT NULL, e.g. `["7H", "AS", "10C", ...]`)
- `total_cards`: `SMALLINT` (NOT NULL)
- `burn_cards`: `SMALLINT` (NOT NULL, default 1)
- `penetration`: `DECIMAL(4, 3)` (NOT NULL)
- `generated_by_session_id`: `UUID` (FK $\rightarrow$ `PLAYER_SESSION.id`, NULL)
- `created_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- **Constraints**: `UNIQUE (simulation_id, shoe_number)`

#### `PLAYER_SHOE_STATE`
Independent consumption tracking per player for a shared shoe.
- `id`: `UUID` (PK)
- `player_session_id`: `UUID` (FK $\rightarrow$ `PLAYER_SESSION.id`, ON DELETE CASCADE, NOT NULL)
- `shoe_id`: `UUID` (FK $\rightarrow$ `SHOE.id`, ON DELETE CASCADE, NOT NULL)
- `current_position`: `INTEGER` (NOT NULL, default 0)
- `cards_seen`: `INTEGER` (NOT NULL, default 0)
- `running_count`: `INTEGER` (NOT NULL, default 0)
- `true_count`: `DECIMAL(6, 2)` (NOT NULL, default 0.0)
- `started_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- `finished_at`: `TIMESTAMPTZ` (NULL)
- **Constraints**: `UNIQUE (player_session_id, shoe_id)`, `CHECK (current_position >= 0)`

---

### 3.4 Game Flow Domain

#### `ROUND`
The common round container within a simulation.
- `id`: `UUID` (PK)
- `simulation_id`: `UUID` (FK $\rightarrow$ `SIMULATION.id`, ON DELETE CASCADE, NOT NULL)
- `round_number`: `INTEGER` (NOT NULL)
- `status`: `round_status` (NOT NULL, default `'IN_PROGRESS'`)
- `dealer_final_value`: `SMALLINT` (NULL)
- `dealer_blackjack`: `BOOLEAN` (NOT NULL, default FALSE)
- `dealer_bust`: `BOOLEAN` (NOT NULL, default FALSE)
- `started_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- `finished_at`: `TIMESTAMPTZ` (NULL)
- **Constraints**: `UNIQUE (simulation_id, round_number)`, `CHECK (round_number > 0)`

#### `ROUND_PLAYER`
A participant's stake and status in a round.
- `id`: `UUID` (PK)
- `round_id`: `UUID` (FK $\rightarrow$ `ROUND.id`, ON DELETE CASCADE, NOT NULL)
- `player_session_id`: `UUID` (FK $\rightarrow$ `PLAYER_SESSION.id`, ON DELETE CASCADE, NOT NULL)
- `bankroll_before`: `DECIMAL(12, 2)` (NOT NULL)
- `bankroll_after`: `DECIMAL(12, 2)` (NULL)
- `status`: `player_round_status` (NOT NULL, default `'ACTIVE'`)
- `started_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- `finished_at`: `TIMESTAMPTZ` (NULL)
- **Constraints**: `UNIQUE (round_id, player_session_id)`

#### `HAND`
A player hand instance, supporting recursive split hierarchies.
- `id`: `UUID` (PK)
- `round_player_id`: `UUID` (FK $\rightarrow$ `ROUND_PLAYER.id`, ON DELETE CASCADE, NOT NULL)
- `parent_hand_id`: `UUID` (FK $\rightarrow$ `HAND.id`, ON DELETE CASCADE, NULL)
- `hand_number`: `SMALLINT` (NOT NULL, default 1)
- `is_initial`: `BOOLEAN` (NOT NULL, default TRUE)
- `is_split`: `BOOLEAN` (NOT NULL, default FALSE)
- `status`: `hand_status` (NOT NULL, default `'IN_PLAY'`)
- `final_value`: `SMALLINT` (NULL)
- `is_blackjack`: `BOOLEAN` (NOT NULL, default FALSE)
- `is_bust`: `BOOLEAN` (NOT NULL, default FALSE)

#### `CARD_EVENT`
Chronological record of every card dealt.
- `id`: `UUID` (PK)
- `round_id`: `UUID` (FK $\rightarrow$ `ROUND.id`, ON DELETE CASCADE, NOT NULL)
- `hand_id`: `UUID` (FK $\rightarrow$ `HAND.id`, ON DELETE CASCADE, NULL — NULL for dealer cards)
- `shoe_id`: `UUID` (FK $\rightarrow$ `SHOE.id`, ON DELETE CASCADE, NOT NULL)
- `recipient`: `card_recipient` (NOT NULL)
- `event_type`: `card_event_type` (NOT NULL, default `'DEAL'`)
- `card`: `VARCHAR(4)` (NOT NULL, e.g. `"AS"`, `"10H"`)
- `sequence_number`: `INTEGER` (NOT NULL)
- `shoe_position`: `INTEGER` (NOT NULL)
- `created_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- **Constraints**: `CHECK (sequence_number > 0)`, `CHECK (shoe_position >= 0)`

---

### 3.5 Decisions & AI Domain

#### `DECISION`
Granular player decision on a hand.
- `id`: `UUID` (PK)
- `hand_id`: `UUID` (FK $\rightarrow$ `HAND.id`, ON DELETE CASCADE, NOT NULL)
- `decision_number`: `INTEGER` (NOT NULL)
- `decision_type`: `decision_type` (NOT NULL)
- `action`: `player_action` (NOT NULL)
- `confidence_pct`: `DECIMAL(5, 2)` (NULL)
- `running_count`: `INTEGER` (NOT NULL)
- `true_count`: `DECIMAL(6, 2)` (NOT NULL)
- `bankroll_at_decision`: `DECIMAL(12, 2)` (NOT NULL)
- `optimal_reference_action`: `player_action` (NOT NULL)
- `agrees_with_optimal`: `BOOLEAN` (NOT NULL)
- `state_snapshot`: `JSONB` (NOT NULL)
- `created_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- **Constraints**: `CHECK (decision_number > 0)`, `CHECK (confidence_pct >= 0.0 AND confidence_pct <= 100.0)`

#### `MODEL_RESPONSE`
Raw AI inference telemetry linked to a decision.
- `id`: `UUID` (PK)
- `decision_id`: `UUID` (FK $\rightarrow$ `DECISION.id`, ON DELETE CASCADE, NOT NULL, UNIQUE)
- `provider`: `model_provider` (NOT NULL)
- `model_name`: `VARCHAR(100)` (NOT NULL)
- `model_version`: `VARCHAR(50)` (NULL)
- `request_payload`: `JSONB` (NOT NULL)
- `response_payload`: `JSONB` (NOT NULL)
- `http_status`: `SMALLINT` (NULL)
- `latency_ms`: `INTEGER` (NOT NULL)
- `error_type`: `VARCHAR(100)` (NULL)
- `error_message`: `TEXT` (NULL)
- `requested_at`: `TIMESTAMPTZ` (NOT NULL)
- `responded_at`: `TIMESTAMPTZ` (NOT NULL)

---

### 3.6 Economy & Ledger Domain

#### `BET`
Monetary wager committed during a round.
- `id`: `UUID` (PK)
- `round_player_id`: `UUID` (FK $\rightarrow$ `ROUND_PLAYER.id`, ON DELETE CASCADE, NOT NULL)
- `hand_id`: `UUID` (FK $\rightarrow$ `HAND.id`, ON DELETE CASCADE, NULL)
- `bet_type`: `bet_type` (NOT NULL)
- `amount`: `DECIMAL(10, 2)` (NOT NULL)
- `created_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- **Constraints**: `CHECK (amount >= 0)`

#### `HAND_RESULT`
Terminal outcome of a hand.
- `id`: `UUID` (PK)
- `hand_id`: `UUID` (FK $\rightarrow$ `HAND.id`, ON DELETE CASCADE, NOT NULL, UNIQUE)
- `result`: `hand_result_type` (NOT NULL)
- `player_value`: `SMALLINT` (NOT NULL)
- `dealer_value`: `SMALLINT` (NOT NULL)
- `payout_amount`: `DECIMAL(10, 2)` (NOT NULL, default 0.0)
- `net_amount`: `DECIMAL(10, 2)` (NOT NULL)
- `created_at`: `TIMESTAMPTZ` (NOT NULL, default: now)

#### `BANKROLL_TRANSACTION`
Immutable double-entry style financial audit entry.
- `id`: `UUID` (PK)
- `round_player_id`: `UUID` (FK $\rightarrow$ `ROUND_PLAYER.id`, ON DELETE CASCADE, NOT NULL)
- `hand_id`: `UUID` (FK $\rightarrow$ `HAND.id`, ON DELETE CASCADE, NULL)
- `bet_id`: `UUID` (FK $\rightarrow$ `BET.id`, ON DELETE CASCADE, NULL)
- `transaction_type`: `transaction_type` (NOT NULL)
- `amount`: `DECIMAL(10, 2)` (NOT NULL — negative for stake out, positive for payout/refund in)
- `balance_before`: `DECIMAL(12, 2)` (NOT NULL)
- `balance_after`: `DECIMAL(12, 2)` (NOT NULL)
- `created_at`: `TIMESTAMPTZ` (NOT NULL, default: now)
- **Invariant**: `balance_after == balance_before + amount`

---

## 4. Query Performance Indexes

```sql
CREATE INDEX idx_simulation_run_id ON simulations(run_id);
CREATE INDEX idx_player_session_sim_type ON player_sessions(simulation_id, player_type);
CREATE INDEX idx_shoe_sim_number ON shoes(simulation_id, shoe_number);
CREATE INDEX idx_player_shoe_state_session_shoe ON player_shoe_states(player_session_id, shoe_id);
CREATE INDEX idx_round_sim_number ON rounds(simulation_id, round_number);
CREATE INDEX idx_round_player_round_session ON round_players(round_id, player_session_id);
CREATE INDEX idx_hand_round_player ON hands(round_player_id);
CREATE INDEX idx_card_event_round_seq ON card_events(round_id, sequence_number);
CREATE INDEX idx_card_event_shoe_pos ON card_events(shoe_id, shoe_position);
CREATE INDEX idx_decision_hand_num ON decisions(hand_id, decision_number);
CREATE INDEX idx_model_response_decision ON model_responses(decision_id);
CREATE INDEX idx_bet_round_player ON bets(round_player_id);
CREATE INDEX idx_bankroll_tx_round_player_created ON bankroll_transactions(round_player_id, created_at);
```
