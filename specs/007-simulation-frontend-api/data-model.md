# Data Model Specification: Simulation Frontend API

**Feature**: `007-simulation-frontend-api`  
**Date**: 2026-10-12  
**Status**: Completed  

---

## 1. Overview

This document specifies the Pydantic v2 schemas, REST request/response data models, WebSocket JSON frame structures, and database export payload definitions used by the Simulation Frontend API.

---

## 2. API Request & Configuration Schemas

### 2.1 `TableRulesConfig`
Configurable casino and table rules matching [`Reglas de BlackJack.md`](../../docs/Reglas%20de%20BlackJack.md):

```python
class Soft17Option(str, Enum):
    STAND = "S17"
    HIT = "H17"

class HoleCardOption(str, Enum):
    AMERICAN_PEEK = "AMERICAN_PEEK"
    EUROPEAN_NO_HOLE_CARD = "EUROPEAN_NO_HOLE_CARD"

class SurrenderOption(str, Enum):
    LATE = "LATE"
    EARLY = "EARLY"
    NO_SURRENDER = "NO_SURRENDER"

class TableRulesConfig(BaseModel):
    soft_17_rule: Soft17Option = Field(default=Soft17Option.STAND, description="Dealer stands on Soft 17 (S17) or hits (H17)")
    blackjack_payout: float = Field(default=1.5, ge=1.0, le=2.0, description="Natural Blackjack payout multiplier: 1.5 (3:2), 1.2 (6:5), 1.0 (1:1)")
    hole_card_rule: HoleCardOption = Field(default=HoleCardOption.AMERICAN_PEEK, description="American peek vs European No Hole Card (ENHC)")
    insurance_allowed: bool = Field(default=True, description="Enable or disable 2:1 insurance side bet")
    surrender_rule: SurrenderOption = Field(default=SurrenderOption.LATE, description="Surrender rule: LATE, EARLY, or NO_SURRENDER")
    double_after_split: bool = Field(default=True, description="Permit doubling down on hands created by splitting (DAS)")
    max_split_hands: int = Field(default=4, ge=1, le=4, description="Maximum simultaneous hands resulting from splits")
    resplit_aces: bool = Field(default=False, description="Allow re-splitting pairs of Aces (RSA)")
    hit_split_aces: bool = Field(default=False, description="Allow drawing more than one card to split Aces")
    num_decks: int = Field(default=6, description="Number of 52-card decks in shoe: 1, 2, 4, 6, 8")
    penetration: float = Field(default=0.75, ge=0.50, le=0.85, description="Shoe cut-card threshold percentage (50% to 85%)")
    burn_cards_count: int = Field(default=0, ge=0, le=5, description="Number of cards discarded upon shoe initialization")
    initial_bankroll: float = Field(default=1000.0, ge=100.0, le=1000000.0, description="Starting bankroll per player table")
    min_bet: float = Field(default=10.0, ge=1.0, le=1000.0, description="Table minimum wager")
    max_bet: float = Field(default=500.0, ge=10.0, le=50000.0, description="Table maximum wager")
    stop_on_all_bankrupt: bool = Field(default=True, description="Halt simulation if all players are eliminated")
```

### 2.2 `SimulationConfigRequest`
Top-level payload submitted to `POST /api/simulations`:

```python
class ExecutionMode(str, Enum):
    VISUALIZED = "visualized"
    FAST_BATCH = "fast_batch"

class SimulationConfigRequest(BaseModel):
    max_rounds: int = Field(default=10, ge=1, le=100000, description="Number of rounds to execute per simulation")
    num_simulations: int = Field(default=1, ge=1, le=1000, description="Number of simulation runs to execute")
    execution_mode: ExecutionMode = Field(default=ExecutionMode.VISUALIZED, description="visualized (turn-by-turn streaming) or fast_batch (high-speed background)")
    delay_ms: float = Field(default=300.0, ge=0.0, le=2000.0, description="Pacing delay in milliseconds between rounds for visualized mode")
    seed: int | None = Field(default=None, description="Deterministic PRNG random seed (auto-generated if omitted)")
    entities: list[str] = Field(default_factory=lambda: ["optimal", "jev", "laya"], description="Active decision providers: any subset of ['optimal', 'jev', 'laya']")
    mock_mode: bool = Field(default=False, description="Use FakeJev/FakeLaya mock agents for offline execution")
    table_rules: TableRulesConfig = Field(default_factory=TableRulesConfig, description="House rules configuration")
```

---

## 3. API Response Schemas

### 3.1 `SimulationResponse`
Returned upon `POST /api/simulations` creation:

```python
class SimulationResponse(BaseModel):
    session_id: str
    run_id: str
    status: str  # INITIALIZING, RUNNING, PAUSED, PAUSED_ERROR, COMPLETED, STOPPED
    execution_mode: ExecutionMode
    current_round: int
    max_rounds: int
    num_simulations: int
    entities: list[str]
    websocket_url: str
    created_at: str
    table_rules: TableRulesConfig
```

### 3.2 `SimulationListItem` & `SimulationListResponse`
Returned upon `GET /api/simulations`:

```python
class EntityMetricSummary(BaseModel):
    entity_id: str
    rounds_played: int
    net_profit: float
    current_bankroll: float
    win_rate: float
    optimality_rate: float

class SimulationListItem(BaseModel):
    run_id: str
    session_id: str
    status: str
    start_time: str
    end_time: str | None
    total_rounds: int
    max_rounds: int
    num_simulations: int
    seed: int
    entities: list[str]
    metrics: dict[str, EntityMetricSummary]

class SimulationListResponse(BaseModel):
    items: list[SimulationListItem]
    total: int
    page: int
    page_size: int
```

### 3.3 `SimulationDetailResponse`
Returned upon `GET /api/simulations/{id}`:
Includes complete run descriptor, configuration snapshot, player session statistics, shoe reshuffle counts, aggregate benchmark comparators, and strategy deviation analytics.

### 3.4 `SimulationDeviationsResponse` & Strategy Deviation Schemas
Returned upon `GET /api/simulations/{session_id}/deviations`:

```python
class DecisionComparisonPayload(BaseModel):
    is_optimal: bool
    optimal_action: str
    actual_action: str
    category: str  # hard_total, soft_total, pair_split, surrender, insurance
    reasoning: str
    is_legal: bool = True

class CategoryDeviationStats(BaseModel):
    total_decisions: int = 0
    deviations: int = 0
    optimality_rate: float = 1.0

class BetSpreadDeviationStats(BaseModel):
    total_bets: int = 0
    suboptimal_bets: int = 0
    total_bet_delta: float = 0.0
    avg_bet_delta: float = 0.0

class EntityDeviationStats(BaseModel):
    entity_id: str
    total_decisions: int = 0
    optimal_decisions: int = 0
    deviations_count: int = 0
    optimality_rate: float = 1.0
    categories: dict[str, CategoryDeviationStats] = Field(
        default_factory=lambda: {
            "hard_total": CategoryDeviationStats(),
            "soft_total": CategoryDeviationStats(),
            "pair_split": CategoryDeviationStats(),
            "surrender": CategoryDeviationStats(),
            "insurance": CategoryDeviationStats(),
        }
    )
    betting_deviations: BetSpreadDeviationStats = Field(default_factory=BetSpreadDeviationStats)

class SimulationDeviationsResponse(BaseModel):
    session_id: str
    current_round: int
    entities: dict[str, EntityDeviationStats]
    updated_at: str
```

### 3.5 `PurgeDatabaseResponse`
Returned upon `DELETE /api/database` / `POST /api/database/clear`:

```python
class PurgeDatabaseResponse(BaseModel):
    status: str = "cleared"
    tables_purged: int = 15
    cleared_tables: list[str]
    timestamp: str
```

---

## 4. WebSocket Message Framing

### 4.1 Client → Server Commands
Frames received over `ws://localhost:8000/ws/simulations/{session_id}`:

```typescript
type ClientCommand =
  | { command: "pause" }
  | { command: "resume" }
  | { command: "step"; level?: "round" | "turn" }
  | { command: "retry"; entity_id: string }
  | { command: "stop" }
  | { command: "set_speed"; delay_ms: number };
```

### 4.2 Server → Client Telemetry Events
Frames broadcast over WebSocket to connected frontend clients:

```typescript
interface WebSocketTelemetryFrame {
  event_type:
    | "SESSION_STARTED"
    | "ROUND_STARTED"
    | "BET_PLACED"
    | "CARD_DEALT"
    | "DECISION_MADE"
    | "ROUND_SETTLED"
    | "SESSION_PAUSED"
    | "SESSION_RESUMED"
    | "SESSION_STEPPED"
    | "SESSION_ERROR"
    | "SESSION_COMPLETED"
    | "SESSION_STOPPED"
    | "SPEED_UPDATED";
  session_id: string;
  round_number: number;
  timestamp: string;
  payload: Record<string, any>;
}
```

#### Detailed Payload Structures:

1. **`DECISION_MADE` Payload**:
   ```json
   {
     "entity_id": "jev",
     "hand_id": "hand-01",
     "action": "hit",
     "player_hand": ["10♠", "6♦"],
     "player_total": 16,
     "is_soft": false,
     "dealer_upcard": "10♥",
     "model": "jev-latest",
     "confidence": 0.89,
     "probabilities": { "hit": 0.89, "stand": 0.11 },
     "latency_ms": 42.5,
     "usage": { "input_tokens": 128, "output_tokens": 14 },
     "comparison": {
       "is_optimal": true,
       "optimal_action": "hit",
       "actual_action": "hit",
       "category": "hard_total",
       "reasoning": "Basic strategy dictates Hit for Hard 16 vs 10",
       "is_legal": true
     }
   }
   ```

2. **`ROUND_SETTLED` Payload**:
   ```json
   {
     "round_number": 5,
     "dealer_hand": ["10♥", "8♠"],
     "dealer_total": 18,
     "results": {
       "jev": { "result": "loss", "payout": -20.0, "bankroll": 980.0 },
       "laya": { "result": "win", "payout": 20.0, "bankroll": 1020.0 },
       "optimal": { "result": "loss", "payout": -20.0, "bankroll": 980.0 }
     },
     "running_deviations": {
       "jev": {
         "total_decisions": 6,
         "optimal_decisions": 5,
         "deviations_count": 1,
         "optimality_rate": 0.833,
         "categories": {
           "hard_total": { "total_decisions": 4, "deviations": 1, "optimality_rate": 0.75 },
           "soft_total": { "total_decisions": 1, "deviations": 0, "optimality_rate": 1.0 },
           "pair_split": { "total_decisions": 1, "deviations": 0, "optimality_rate": 1.0 },
           "surrender": { "total_decisions": 0, "deviations": 0, "optimality_rate": 1.0 }
         },
         "betting_deviations": {
           "total_bets": 5,
           "suboptimal_bets": 1,
           "total_bet_delta": 10.0,
           "avg_bet_delta": 2.0
         }
       },
       "laya": {
         "total_decisions": 5,
         "optimal_decisions": 5,
         "deviations_count": 0,
         "optimality_rate": 1.0,
         "categories": { "hard_total": { "total_decisions": 5, "deviations": 0, "optimality_rate": 1.0 } },
         "betting_deviations": { "total_bets": 5, "suboptimal_bets": 0, "total_bet_delta": 0.0, "avg_bet_delta": 0.0 }
       },
       "optimal": {
         "total_decisions": 5,
         "optimal_decisions": 5,
         "deviations_count": 0,
         "optimality_rate": 1.0,
         "categories": { "hard_total": { "total_decisions": 5, "deviations": 0, "optimality_rate": 1.0 } },
         "betting_deviations": { "total_bets": 5, "suboptimal_bets": 0, "total_bet_delta": 0.0, "avg_bet_delta": 0.0 }
       }
     }
   }
   ```

3. **`SESSION_ERROR` Payload**:
   ```json
   {
     "entity_id": "jev",
     "error": "TypeSafe request timed out after 15.0s",
     "status": "PAUSED_ERROR",
     "allowed_actions": ["retry", "abort"]
   }
   ```

---

## 5. Hierarchical JSON Export Schema

Matches `RunExporter` specification in `backend/app/persistence/exporter.py`:

```json
{
  "run": {
    "id": "e8a1f77d-78be-40f1-9430-8018e690cf85",
    "name": "Multi-Agent Comparison Experiment",
    "status": "COMPLETED",
    "started_at": "2026-10-12T20:00:00Z",
    "completed_at": "2026-10-12T20:05:00Z",
    "configuration": {
      "rules": { ... },
      "seed": 42,
      "max_rounds": 100
    },
    "simulations": [
      {
        "simulation_number": 1,
        "status": "COMPLETED",
        "player_sessions": [
          {
            "entity_id": "jev",
            "starting_bankroll": 1000.0,
            "final_bankroll": 1150.0,
            "net_profit": 150.0,
            "wins": 45,
            "losses": 40,
            "pushes": 15,
            "optimality_rate": 0.94
          }
        ],
        "rounds": [
          {
            "round_number": 1,
            "dealer_cards": ["10♥", "7♦"],
            "dealer_total": 17,
            "players": [
              {
                "entity_id": "jev",
                "hands": [
                  {
                    "cards": ["K♠", "8♦"],
                    "total": 18,
                    "result": "win",
                    "payout": 10.0,
                    "decisions": [
                      {
                        "action": "stand",
                        "confidence": 0.98,
                        "probabilities": { "stand": 0.98, "hit": 0.02 },
                        "latency_ms": 35.0,
                        "is_optimal": true
                      }
                    ]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```
