import { EntityId, ExecutionMode, Soft17Rule, HoleCardRule, SurrenderRule } from './simulation';

export interface TableRulesConfigPayload {
  soft_17_rule: Soft17Rule;
  blackjack_payout: number;
  hole_card_rule: HoleCardRule;
  insurance_allowed: boolean;
  surrender_rule: SurrenderRule;
  double_after_split: boolean;
  max_split_hands: number;
  resplit_aces: boolean;
  hit_split_aces: boolean;
  num_decks: number;
  penetration: number;
  burn_cards_count: number;
  initial_bankroll: number;
  min_bet: number;
  max_bet: number;
  stop_on_all_bankrupt: boolean;
}

export interface CreateSimulationPayload {
  max_rounds: number;
  num_simulations: number;
  execution_mode: ExecutionMode;
  delay_ms: number;
  seed: number | null;
  entities: EntityId[];
  mock_mode: boolean;
  table_rules: TableRulesConfigPayload;
}

export interface SimulationResponse {
  session_id: string;
  run_id: string;
  status: string;
  execution_mode: ExecutionMode;
  current_round: number;
  max_rounds: number;
  num_simulations: number;
  entities: string[];
  websocket_url: string;
  created_at: string;
  table_rules: TableRulesConfigPayload;
}

export interface PurgeDatabaseResponse {
  status: string;
  message?: string;
  tables_purged?: number;
  cleared_tables?: string[];
  tables_cleared?: string[];
  records_deleted?: number;
  duration_ms?: number;
  timestamp?: string;
}

export type OutboundCommand =
  | { command: 'start' }
  | { command: 'pause' }
  | { command: 'resume' }
  | { command: 'step'; level?: 'round' | 'turn' }
  | { command: 'retry'; entity_id?: string }
  | { command: 'stop' }
  | { command: 'set_speed'; delay_ms: number };

export interface BaseTelemetryEvent<T = Record<string, any>> {
  event_type: string;
  session_id: string;
  round_number: number;
  timestamp: string;
  payload: T;
}

export interface SessionSnapshotPayload {
  status: string;
  execution_mode: ExecutionMode;
  delay_ms: number;
  max_rounds: number;
  current_round: number;
  entities: string[];
  tables: Record<
    string,
    {
      bankroll: number;
      rounds_played: number;
      shoe_generation?: number;
      cards_remaining?: number;
      running_count?: number;
      true_count?: number;
    }
  >;
  deviations?: Record<string, any>;
}

export interface CardDealtPayload {
  recipient: 'dealer' | EntityId;
  card: string; // e.g. "10♠"
  rank: string;
  suit: string;
  is_hole_card?: boolean;
  hand_index?: number;
  is_double_down?: boolean;
  total?: number;
  is_soft?: boolean;
  is_busted?: boolean;
}

export interface DecisionMadePayload {
  entity_id: EntityId;
  action: string;
  hand_index?: number;
  confidence?: number;
  comparison?: {
    is_optimal: boolean;
    optimal_action: string;
    actual_action: string;
    category: string;
    reasoning: string;
    is_legal?: boolean;
  };
  is_optimal?: boolean;
  optimal_action?: string;
}

export interface RoundSettledPayload {
  round_number: number;
  dealer_cards: string[];
  dealer_total: number;
  dealer_is_busted?: boolean;
  settlements: Record<
    string,
    {
      net_payout: number;
      final_bankroll: number;
      result: 'win' | 'loss' | 'push' | 'blackjack' | 'surrender';
      hands?: Array<{
        total: number;
        payout: number;
        result: string;
      }>;
    }
  >;
  running_deviations?: Record<
    string,
    {
      total_decisions: number;
      optimal_decisions: number;
      suboptimal_decisions: number;
      optimality_rate?: number;
      agreement_rate?: number;
    }
  >;
}

export interface SessionErrorPayload {
  entity_id: string;
  error_message: string;
  is_recoverable: boolean;
  allowed_actions?: string[];
}

export interface SessionCompletedPayload {
  total_rounds: number;
  final_deviations?: Record<
    string,
    {
      total_decisions: number;
      optimal_decisions: number;
      suboptimal_decisions: number;
      agreement_rate: number;
    }
  >;
  summary?: Record<
    string,
    {
      final_bankroll: number;
      net_profit: number;
      win_rate: number;
      optimality_rate: number;
    }
  >;
}

export type InboundTelemetryEvent =
  | BaseTelemetryEvent<SessionSnapshotPayload> & { event_type: 'SESSION_SNAPSHOT' }
  | BaseTelemetryEvent<Record<string, any>> & { event_type: 'ROUND_STARTED' }
  | BaseTelemetryEvent<CardDealtPayload> & { event_type: 'CARD_DEALT' }
  | BaseTelemetryEvent<DecisionMadePayload> & { event_type: 'DECISION_MADE' }
  | BaseTelemetryEvent<RoundSettledPayload> & { event_type: 'ROUND_SETTLED' }
  | BaseTelemetryEvent<{ entity_id: string; generation: number; shoe_number?: number; message?: string }> & {
      event_type: 'SHOE_RESHUFFLED';
    }
  | BaseTelemetryEvent<{ delay_ms: number }> & { event_type: 'SPEED_UPDATED' }
  | BaseTelemetryEvent<SessionErrorPayload> & { event_type: 'SESSION_ERROR' }
  | BaseTelemetryEvent<SessionCompletedPayload> & { event_type: 'SESSION_COMPLETED' }
  | BaseTelemetryEvent<Record<string, any>>;
