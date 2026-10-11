-- Decision_Blackjack Relational Schema Migration (PostgreSQL 16)
-- Conforms strictly to docs/Diseño Base de Datos (Modelo ER).md and data-model.md

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- ENUM TYPES
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE run_status AS ENUM ('CREATED', 'RUNNING', 'PAUSE_REQUESTED', 'PAUSED', 'ERROR', 'COMPLETED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE simulation_status AS ENUM ('RUNNING', 'COMPLETED', 'BANKRUPT', 'ERROR', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE player_type AS ENUM ('JEV', 'LAYA', 'OPTIMAL');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE session_status AS ENUM ('ACTIVE', 'COMPLETED', 'BANKRUPT', 'ERROR');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE termination_reason AS ENUM ('ROUNDS_COMPLETED', 'ALL_BANKRUPT', 'USER_STOPPED', 'ERROR');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE round_status AS ENUM ('IN_PROGRESS', 'COMPLETED', 'ERROR');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE player_round_status AS ENUM ('ACTIVE', 'RESOLVED', 'BUSTED', 'SURRENDERED', 'BLACKJACK');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE hand_status AS ENUM ('IN_PLAY', 'RESOLVED', 'BUSTED', 'DOUBLED', 'SURRENDERED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE card_recipient AS ENUM ('DEALER', 'HAND');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE card_event_type AS ENUM ('DEAL', 'BURN', 'REVEAL');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE decision_type AS ENUM ('INITIAL', 'AFTER_HIT', 'AFTER_SPLIT', 'INSURANCE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE player_action AS ENUM ('HIT', 'STAND', 'DOUBLE', 'SPLIT', 'SURRENDER', 'INSURANCE_ACCEPT', 'INSURANCE_DECLINE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE model_provider AS ENUM ('SYSTEM_ONE', 'LOCAL_MODEL', 'BASIC_STRATEGY');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE bet_type AS ENUM ('INITIAL', 'DOUBLE', 'SPLIT', 'INSURANCE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE hand_result_type AS ENUM ('WIN', 'LOSS', 'PUSH', 'BLACKJACK', 'BUST', 'SURRENDER');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE transaction_type AS ENUM ('BET', 'PAYOUT', 'REFUND', 'INSURANCE', 'SURRENDER', 'ADJUSTMENT');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE soft_17_rule AS ENUM ('STAND', 'HIT');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE hole_card_rule AS ENUM ('AMERICAN_PEEK', 'ENHC');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE split_aces_blackjack_rule AS ENUM ('NATURAL', 'COUNT_21');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE surrender_rule AS ENUM ('NONE', 'LATE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE charlie_rule AS ENUM ('NONE', 'FIVE_CARD', 'SIX_CARD', 'SEVEN_CARD');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================================================
-- 1. EXECUTION DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status run_status NOT NULL DEFAULT 'CREATED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_message TEXT,
    data_directory TEXT
);

CREATE TABLE IF NOT EXISTS run_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL UNIQUE REFERENCES runs(id) ON DELETE CASCADE,
    
    -- Table Rules
    soft_17_rule soft_17_rule NOT NULL,
    blackjack_payout_ratio NUMERIC(5, 3) NOT NULL,
    split_aces_blackjack_rule split_aces_blackjack_rule NOT NULL,
    hole_card_rule hole_card_rule NOT NULL,
    insurance_enabled BOOLEAN NOT NULL,
    insurance_payout_ratio NUMERIC(5, 3) NOT NULL DEFAULT 2.000,
    surrender_rule surrender_rule NOT NULL,
    das_enabled BOOLEAN NOT NULL,
    max_resplit SMALLINT NOT NULL DEFAULT 3,
    rsa_enabled BOOLEAN NOT NULL,
    hit_split_aces BOOLEAN NOT NULL,
    charlie_rule charlie_rule NOT NULL DEFAULT 'NONE',
    number_of_decks SMALLINT NOT NULL DEFAULT 6,
    penetration NUMERIC(4, 3) NOT NULL,
    burn_cards SMALLINT NOT NULL DEFAULT 1,
    initial_bankroll NUMERIC(12, 2) NOT NULL,
    minimum_bet NUMERIC(10, 2) NOT NULL,
    maximum_bet NUMERIC(10, 2) NOT NULL,
    
    -- Experiment Setup
    rounds_per_simulation INTEGER NOT NULL,
    rounds_indefinite BOOLEAN NOT NULL DEFAULT FALSE,
    simulations_count INTEGER NOT NULL DEFAULT 1,
    simulations_indefinite BOOLEAN NOT NULL DEFAULT FALSE,
    user_seed BIGINT,
    optimal_bet_spread JSONB
);

CREATE TABLE IF NOT EXISTS simulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    simulation_number INTEGER NOT NULL CHECK (simulation_number > 0),
    seed BIGINT NOT NULL,
    status simulation_status NOT NULL DEFAULT 'RUNNING',
    initial_bankroll NUMERIC(12, 2) NOT NULL,
    final_bankroll NUMERIC(12, 2),
    termination_reason termination_reason,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    CONSTRAINT uq_simulation_run_number UNIQUE (run_id, simulation_number)
);

-- ============================================================================
-- 2. PARTICIPANTS DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS player_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id UUID NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    player_type player_type NOT NULL,
    initial_bankroll NUMERIC(12, 2) NOT NULL,
    current_bankroll NUMERIC(12, 2) NOT NULL,
    status session_status NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT uq_player_session_sim_type UNIQUE (simulation_id, player_type)
);

-- ============================================================================
-- 3. SHOES DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS shoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id UUID NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    shoe_number INTEGER NOT NULL,
    seed BIGINT NOT NULL,
    card_order JSONB NOT NULL,
    total_cards SMALLINT NOT NULL,
    burn_cards SMALLINT NOT NULL DEFAULT 1,
    penetration NUMERIC(4, 3) NOT NULL,
    generated_by_session_id UUID REFERENCES player_sessions(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT uq_shoe_sim_number UNIQUE (simulation_id, shoe_number)
);

CREATE TABLE IF NOT EXISTS player_shoe_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_session_id UUID NOT NULL REFERENCES player_sessions(id) ON DELETE CASCADE,
    shoe_id UUID NOT NULL REFERENCES shoes(id) ON DELETE CASCADE,
    current_position INTEGER NOT NULL DEFAULT 0 CHECK (current_position >= 0),
    cards_seen INTEGER NOT NULL DEFAULT 0,
    running_count INTEGER NOT NULL DEFAULT 0,
    true_count NUMERIC(6, 2) NOT NULL DEFAULT 0.00,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    CONSTRAINT uq_player_shoe_state_session_shoe UNIQUE (player_session_id, shoe_id)
);

-- ============================================================================
-- 4. GAME FLOW DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_id UUID NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL CHECK (round_number > 0),
    status round_status NOT NULL DEFAULT 'IN_PROGRESS',
    dealer_final_value SMALLINT,
    dealer_blackjack BOOLEAN NOT NULL DEFAULT FALSE,
    dealer_bust BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    CONSTRAINT uq_round_sim_number UNIQUE (simulation_id, round_number)
);

CREATE TABLE IF NOT EXISTS round_players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    player_session_id UUID NOT NULL REFERENCES player_sessions(id) ON DELETE CASCADE,
    bankroll_before NUMERIC(12, 2) NOT NULL,
    bankroll_after NUMERIC(12, 2),
    status player_round_status NOT NULL DEFAULT 'ACTIVE',
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    CONSTRAINT uq_round_player_round_session UNIQUE (round_id, player_session_id)
);

CREATE TABLE IF NOT EXISTS hands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_player_id UUID NOT NULL REFERENCES round_players(id) ON DELETE CASCADE,
    parent_hand_id UUID REFERENCES hands(id) ON DELETE CASCADE,
    hand_number SMALLINT NOT NULL DEFAULT 1,
    is_initial BOOLEAN NOT NULL DEFAULT TRUE,
    is_split BOOLEAN NOT NULL DEFAULT FALSE,
    status hand_status NOT NULL DEFAULT 'IN_PLAY',
    final_value SMALLINT,
    is_blackjack BOOLEAN NOT NULL DEFAULT FALSE,
    is_bust BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS card_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_id UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
    hand_id UUID REFERENCES hands(id) ON DELETE CASCADE,
    shoe_id UUID NOT NULL REFERENCES shoes(id) ON DELETE CASCADE,
    recipient card_recipient NOT NULL,
    event_type card_event_type NOT NULL DEFAULT 'DEAL',
    card VARCHAR(4) NOT NULL,
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    shoe_position INTEGER NOT NULL CHECK (shoe_position >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- ============================================================================
-- 5. DECISIONS & AI DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hand_id UUID NOT NULL REFERENCES hands(id) ON DELETE CASCADE,
    decision_number INTEGER NOT NULL CHECK (decision_number > 0),
    decision_type decision_type NOT NULL,
    action player_action NOT NULL,
    confidence_pct NUMERIC(5, 2) CHECK (confidence_pct >= 0.0 AND confidence_pct <= 100.0),
    running_count INTEGER NOT NULL,
    true_count NUMERIC(6, 2) NOT NULL,
    bankroll_at_decision NUMERIC(12, 2) NOT NULL,
    optimal_reference_action player_action NOT NULL,
    agrees_with_optimal BOOLEAN NOT NULL,
    state_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS model_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL UNIQUE REFERENCES decisions(id) ON DELETE CASCADE,
    provider model_provider NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    request_payload JSONB NOT NULL,
    response_payload JSONB NOT NULL,
    http_status SMALLINT,
    latency_ms INTEGER NOT NULL,
    error_type VARCHAR(100),
    error_message TEXT,
    requested_at TIMESTAMPTZ NOT NULL,
    responded_at TIMESTAMPTZ NOT NULL
);

-- ============================================================================
-- 6. ECONOMY DOMAIN
-- ============================================================================

CREATE TABLE IF NOT EXISTS bets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_player_id UUID NOT NULL REFERENCES round_players(id) ON DELETE CASCADE,
    hand_id UUID REFERENCES hands(id) ON DELETE CASCADE,
    bet_type bet_type NOT NULL,
    amount NUMERIC(10, 2) NOT NULL CHECK (amount >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS hand_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hand_id UUID NOT NULL UNIQUE REFERENCES hands(id) ON DELETE CASCADE,
    result hand_result_type NOT NULL,
    player_value SMALLINT NOT NULL,
    dealer_value SMALLINT NOT NULL,
    payout_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    net_amount NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS bankroll_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_player_id UUID NOT NULL REFERENCES round_players(id) ON DELETE CASCADE,
    hand_id UUID REFERENCES hands(id) ON DELETE CASCADE,
    bet_id UUID REFERENCES bets(id) ON DELETE CASCADE,
    transaction_type transaction_type NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    balance_before NUMERIC(12, 2) NOT NULL,
    balance_after NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- ============================================================================
-- 7. PERFORMANCE INDEXES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_simulation_run_id ON simulations(run_id);
CREATE INDEX IF NOT EXISTS idx_player_session_sim_type ON player_sessions(simulation_id, player_type);
CREATE INDEX IF NOT EXISTS idx_shoe_sim_number ON shoes(simulation_id, shoe_number);
CREATE INDEX IF NOT EXISTS idx_player_shoe_state_session_shoe ON player_shoe_states(player_session_id, shoe_id);
CREATE INDEX IF NOT EXISTS idx_round_sim_number ON rounds(simulation_id, round_number);
CREATE INDEX IF NOT EXISTS idx_round_player_round_session ON round_players(round_id, player_session_id);
CREATE INDEX IF NOT EXISTS idx_hand_round_player ON hands(round_player_id);
CREATE INDEX IF NOT EXISTS idx_card_event_round_seq ON card_events(round_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_card_event_shoe_pos ON card_events(shoe_id, shoe_position);
CREATE INDEX IF NOT EXISTS idx_decision_hand_num ON decisions(hand_id, decision_number);
CREATE INDEX IF NOT EXISTS idx_model_response_decision ON model_responses(decision_id);
CREATE INDEX IF NOT EXISTS idx_bet_round_player ON bets(round_player_id);
CREATE INDEX IF NOT EXISTS idx_bankroll_tx_round_player_created ON bankroll_transactions(round_player_id, created_at);
