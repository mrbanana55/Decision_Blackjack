export type Soft17Rule = 'S17' | 'H17';
export type BlackjackPayout = 1.5 | 1.2 | 1.0;
export type HoleCardRule = 'AMERICAN_PEEK' | 'EUROPEAN_NO_HOLE_CARD';
export type SurrenderRule = 'LATE' | 'EARLY' | 'NO_SURRENDER';
export type ExecutionMode = 'visualized' | 'fast_batch';
export type EntityId = 'jev' | 'laya' | 'optimal';

export interface VariantRulesFormValues {
  // Dealer & Table Rules
  soft_17_rule: Soft17Rule;
  blackjack_payout: BlackjackPayout;
  hole_card_rule: HoleCardRule;
  insurance_allowed: boolean;
  surrender_rule: SurrenderRule;

  // Player Splits & Double Rules
  double_after_split: boolean;
  max_split_hands: number; // 1 to 4
  resplit_aces: boolean;
  hit_split_aces: boolean;

  // Shoe & Deck Setup
  num_decks: 1 | 2 | 4 | 6 | 8;
  penetration: number; // 0.50 to 0.85
  burn_cards_count: number; // 0 to 5

  // Economics & Limits
  initial_bankroll: number; // >= 10.0
  min_bet: number; // >= 1.0
  max_bet: number; // >= min_bet
  stop_on_all_bankrupt: boolean;

  // Simulation Scope & Operational Controls
  max_rounds: number; // 1 to 100,000
  num_simulations: number; // 1 to 1,000
  seed: number | null; // optional integer
  execution_mode: ExecutionMode;
  delay_ms: number; // 0 to 2,000
  mock_mode: boolean;

  // Player Selection (FR-001)
  selected_players: {
    jev: boolean;
    laya: boolean;
    optimal: boolean;
  };
}

export const DEFAULT_VARIANT_RULES: VariantRulesFormValues = {
  soft_17_rule: 'S17',
  blackjack_payout: 1.5,
  hole_card_rule: 'AMERICAN_PEEK',
  insurance_allowed: true,
  surrender_rule: 'LATE',
  double_after_split: true,
  max_split_hands: 4,
  resplit_aces: false,
  hit_split_aces: false,
  num_decks: 6,
  penetration: 0.75,
  burn_cards_count: 0,
  initial_bankroll: 1000.0,
  min_bet: 10.0,
  max_bet: 500.0,
  stop_on_all_bankrupt: true,
  max_rounds: 100,
  num_simulations: 1,
  seed: null,
  execution_mode: 'visualized',
  delay_ms: 300,
  mock_mode: false,
  selected_players: {
    jev: true,
    laya: true,
    optimal: true,
  },
};

export interface CardVisualState {
  id: string; // unique card render id (e.g., "card-jev-0-1")
  card_str: string; // "10♠", "A♥", "K♦", "7♣"
  rank: string; // "10", "A", "K", "7"
  suit: 'spades' | 'hearts' | 'diamonds' | 'clubs';
  svg_path: string; // URL to svg
  is_hidden: boolean; // true for dealer face-down hole card
  is_horizontal: boolean; // true if dealt on double down (rotated 90deg)
  is_split: boolean;
}

export interface PlayerHandState {
  hand_id: string;
  cards: CardVisualState[];
  total: number;
  is_soft: boolean;
  is_busted: boolean;
  is_blackjack: boolean;
  is_doubled: boolean;
  is_surrendered: boolean;
}

export interface DecisionComparison {
  is_optimal: boolean;
  optimal_action: string;
  actual_action?: string;
  category: string;
  reasoning: string;
  is_legal?: boolean;
}

export interface WinLossPushStats {
  wins: number;
  losses: number;
  pushes: number;
  total: number;
}

export interface PlayerTableState {
  entity_id: EntityId;
  name: string; // "Jev (System One)", "Laya (Local)", "Basic Strategy"
  carpet_color: string; // "rgb(213, 120, 190)", "rgb(68, 120, 208)", "rgb(118, 194, 154)"
  is_selected: boolean; // false -> empty table, darkened stats
  is_bankrupt: boolean;
  shoe_generation: number;
  is_shuffling: boolean;
  cards_remaining: number;
  running_count: number;
  true_count: number;

  // Table Cards (Top Row)
  dealer_cards: CardVisualState[];
  dealer_total: number;
  dealer_is_busted: boolean;
  player_hands: PlayerHandState[];
  active_hand_index: number;

  // Live Stats (Bottom Row)
  current_bet: number;
  last_action: string | null; // "HIT", "STAND", "DOUBLE", "SPLIT", "SURRENDER"
  last_comparison: DecisionComparison | null;

  // Financial State
  current_bankroll: number;
  starting_bankroll: number;
  net_profit_delta: number; // e.g. +50.0

  // 3 Dynamic Graph Bars Data
  optimality_rate: number; // 0.0 to 1.0 (Basic Strategy agreement %)
  win_loss_push: WinLossPushStats;
  relative_bankroll_pct: number; // (current / initial) * 100
}

export type SimulationLifecycle =
  | 'INITIALIZING'
  | 'RUNNING'
  | 'PAUSED'
  | 'PAUSED_ERROR'
  | 'COMPLETED';

export interface ActiveFault {
  entity_id: string;
  error_message: string;
  is_recoverable: boolean;
}

export interface CompletionPlayerSummary {
  final_bankroll: number;
  net_profit: number;
  win_rate: number;
  optimality_rate: number;
}

export interface CompletionSummary {
  total_rounds: number;
  players: Record<EntityId, CompletionPlayerSummary>;
}

export interface SimulationSessionState {
  session_id: string | null;
  run_id: string | null;
  status: SimulationLifecycle;
  execution_mode: ExecutionMode;
  current_round: number;
  max_rounds: number;
  shoe_generation: number;
  delay_ms: number;
  rules: VariantRulesFormValues | null;

  // 3 Player Columns
  tables: Record<EntityId, PlayerTableState>;

  // RNF-02 Fault Notification
  active_fault: ActiveFault | null;

  // Completion Summary
  completion_summary: CompletionSummary | null;
}
