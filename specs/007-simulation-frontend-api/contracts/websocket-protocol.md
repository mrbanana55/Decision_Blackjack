# WebSocket Protocol Contract: Simulation Telemetry & Flow Control

**Feature**: `007-simulation-frontend-api`  
**Endpoint**: `ws://localhost:8000/ws/simulations/{session_id}`  
**Protocol Version**: `1.0.0`  

---

## 1. Overview

This contract defines the bidirectional JSON messaging protocol between frontend clients and the FastAPI backend over native WebSockets. The connection serves two functions:
1. **Server → Client**: Continuous streaming of granular game events, AI inference telemetry, bankroll adjustments, and benchmark comparisons.
2. **Client → Server**: Instant interactive flow control (`pause`, `resume`, `step`, `retry`, `stop`) and dynamic playback speed adjustment (`set_speed`).

---

## 2. Connection Handshake & Lifecycle

1. **Connection URL**: `ws://<host>:8000/ws/simulations/{session_id}`
2. **Path Parameter**: `{session_id}` must match an active or initialized simulation session created via `POST /api/simulations`.
3. **Invalid Session**: If `{session_id}` is not found or already purged, the server closes the connection immediately with close code `4404` (`Session Not Found`).
4. **Initial Snapshot**: Upon successful handshake, the server sends an immediate `SESSION_SNAPSHOT` frame conveying the current status, current round, configured rules, and initial or current table metrics.
5. **Heartbeat / Ping-Pong**: The client or server may send standard WebSocket ping/pong frames to keep connections alive through proxies.

---

## 3. Client → Server Commands

Clients send JSON text frames with a mandatory `command` property:

### 3.1 Pause
Suspends simulation execution at the next round/turn boundary:
```json
{
  "command": "pause"
}
```

### 3.2 Resume
Resumes an idle paused simulation:
```json
{
  "command": "resume"
}
```

### 3.3 Step
Advances execution by exactly one round or one turn, then re-pauses:
```json
{
  "command": "step",
  "level": "round"
}
```
*Note*: `level` defaults to `"round"`, or may be `"turn"`.

### 3.4 Retry (Fault Recovery)
Retries an entity turn following an external API timeout or rate limit (`PAUSED_ERROR`):
```json
{
  "command": "retry",
  "entity_id": "jev"
}
```

### 3.5 Stop
Cancels ongoing simulation execution and finalizes session metrics:
```json
{
  "command": "stop"
}
```

### 3.6 Set Speed (Dynamic Pacing Delay)
Adjusts pacing delay between rounds on the fly during visualized mode:
```json
{
  "command": "set_speed",
  "delay_ms": 150.0
}
```
*Note*: `delay_ms` must be between `0.0` (unthrottled) and `2000.0`.

---

## 4. Server → Client Telemetry Event Frames

Every server broadcast has the following envelope structure:

```json
{
  "event_type": "<EVENT_TYPE>",
  "session_id": "sim-c5a4b123",
  "round_number": 3,
  "timestamp": "2026-10-12T21:40:00.123456Z",
  "payload": { ... }
}
```

### 4.1 Event Catalog

#### 1. `SESSION_SNAPSHOT`
Emitted immediately upon client connection:
```json
{
  "event_type": "SESSION_SNAPSHOT",
  "session_id": "sim-c5a4b123",
  "round_number": 2,
  "timestamp": "2026-10-12T21:40:00Z",
  "payload": {
    "status": "RUNNING",
    "execution_mode": "visualized",
    "delay_ms": 300.0,
    "max_rounds": 10,
    "current_round": 2,
    "entities": ["optimal", "jev", "laya"],
    "tables": {
      "jev": { "bankroll": 980.0, "rounds_played": 2 },
      "laya": { "bankroll": 1020.0, "rounds_played": 2 },
      "optimal": { "bankroll": 1000.0, "rounds_played": 2 }
    },
    "deviations": {
      "jev": { "total_decisions": 2, "deviations_count": 0, "optimality_rate": 1.0 },
      "laya": { "total_decisions": 2, "deviations_count": 0, "optimality_rate": 1.0 },
      "optimal": { "total_decisions": 2, "deviations_count": 0, "optimality_rate": 1.0 }
    }
  }
}
```

#### 2. `ROUND_STARTED`
Emitted at the opening of each round:
```json
{
  "event_type": "ROUND_STARTED",
  "session_id": "sim-c5a4b123",
  "round_number": 3,
  "timestamp": "2026-10-12T21:40:01Z",
  "payload": {
    "round_number": 3,
    "shoe_generation": 0
  }
}
```

#### 3. `BET_PLACED`
Emitted when an entity places its opening round wager:
```json
{
  "event_type": "BET_PLACED",
  "session_id": "sim-c5a4b123",
  "round_number": 3,
  "timestamp": "2026-10-12T21:40:01.050Z",
  "payload": {
    "entity_id": "jev",
    "amount": 20.0,
    "multiplier": "2x",
    "bankroll_before": 980.0,
    "bankroll_after": 960.0
  }
}
```

#### 4. `CARD_DEALT`
Emitted for initial deals and hit draws:
```json
{
  "event_type": "CARD_DEALT",
  "session_id": "sim-c5a4b123",
  "round_number": 3,
  "timestamp": "2026-10-12T21:40:01.100Z",
  "payload": {
    "recipient": "jev",
    "card": "10♠",
    "hand_index": 0,
    "is_dealer_upcard": false,
    "hand_total": 16,
    "is_soft": false
  }
}
```

#### 5. `DECISION_MADE`
Emitted when any entity (Jev, Laya, or Basic Strategy) makes an in-hand action decision:
```json
{
  "event_type": "DECISION_MADE",
  "session_id": "sim-c5a4b123",
  "round_number": 3,
  "timestamp": "2026-10-12T21:40:01.350Z",
  "payload": {
    "entity_id": "jev",
    "hand_id": "hand-01",
    "action": "hit",
    "player_cards": ["10♠", "6♦"],
    "player_total": 16,
    "dealer_upcard": "10♥",
    "model_name": "jev-latest",
    "confidence": 0.88,
    "probabilities": {
      "hit": 0.88,
      "stand": 0.12
    },
    "latency_ms": 45.2,
    "usage": {
      "input_tokens": 128,
      "output_tokens": 14
    },
    "comparison": {
      "is_optimal": true,
      "optimal_action": "hit",
      "actual_action": "hit",
      "category": "hard_total",
      "reasoning": "Basic strategy dictates Hit for Hard 16 vs 10",
      "is_legal": true
    }
  }
}
```

#### 6. `ROUND_SETTLED`
Emitted when all hands are resolved and dealer completes actions:
```json
{
  "event_type": "ROUND_SETTLED",
  "session_id": "sim-c5a4b123",
  "round_number": 3,
  "timestamp": "2026-10-12T21:40:02Z",
  "payload": {
    "dealer_cards": ["10♥", "8♠"],
    "dealer_total": 18,
    "dealer_busted": false,
    "settlements": {
      "jev": { "result": "win", "payout": 20.0, "net_profit": 20.0, "current_bankroll": 1000.0 },
      "laya": { "result": "loss", "payout": -20.0, "net_profit": 0.0, "current_bankroll": 1000.0 },
      "optimal": { "result": "win", "payout": 20.0, "net_profit": 20.0, "current_bankroll": 1020.0 }
    },
    "running_deviations": {
      "jev": {
        "total_decisions": 3,
        "optimal_decisions": 3,
        "deviations_count": 0,
        "optimality_rate": 1.0,
        "categories": {
          "hard_total": { "total_decisions": 2, "deviations": 0, "optimality_rate": 1.0 },
          "soft_total": { "total_decisions": 1, "deviations": 0, "optimality_rate": 1.0 }
        },
        "betting_deviations": {
          "total_bets": 3,
          "suboptimal_bets": 0,
          "total_bet_delta": 0.0,
          "avg_bet_delta": 0.0
        }
      },
      "laya": {
        "total_decisions": 3,
        "optimal_decisions": 2,
        "deviations_count": 1,
        "optimality_rate": 0.667,
        "categories": {
          "hard_total": { "total_decisions": 3, "deviations": 1, "optimality_rate": 0.667 }
        },
        "betting_deviations": {
          "total_bets": 3,
          "suboptimal_bets": 0,
          "total_bet_delta": 0.0,
          "avg_bet_delta": 0.0
        }
      },
      "optimal": {
        "total_decisions": 3,
        "optimal_decisions": 3,
        "deviations_count": 0,
        "optimality_rate": 1.0,
        "categories": {
          "hard_total": { "total_decisions": 3, "deviations": 0, "optimality_rate": 1.0 }
        },
        "betting_deviations": {
          "total_bets": 3,
          "suboptimal_bets": 0,
          "total_bet_delta": 0.0,
          "avg_bet_delta": 0.0
        }
      }
    }
  }
}
```

#### 7. `SESSION_PAUSED` / `SESSION_RESUMED` / `SESSION_STEPPED`
```json
{
  "event_type": "SESSION_PAUSED",
  "session_id": "sim-c5a4b123",
  "round_number": 3,
  "timestamp": "2026-10-12T21:40:02.500Z",
  "payload": { "round": 3, "status": "PAUSED" }
}
```

#### 8. `SESSION_ERROR` (RNF-02 Fault Notification)
```json
{
  "event_type": "SESSION_ERROR",
  "session_id": "sim-c5a4b123",
  "round_number": 3,
  "timestamp": "2026-10-12T21:40:03Z",
  "payload": {
    "entity_id": "jev",
    "error": "TypeSafe System One timeout after 15.0s",
    "status": "PAUSED_ERROR",
    "allowed_actions": ["retry", "abort"]
  }
}
```

#### 9. `SESSION_COMPLETED`
```json
{
  "event_type": "SESSION_COMPLETED",
  "session_id": "sim-c5a4b123",
  "round_number": 10,
  "timestamp": "2026-10-12T21:40:10Z",
  "payload": {
    "total_rounds": 10,
    "status": "COMPLETED",
    "summary": {
      "jev": { "net_profit": 50.0, "win_rate": 0.50, "optimality_rate": 0.95 },
      "laya": { "net_profit": -20.0, "win_rate": 0.40, "optimality_rate": 0.88 },
      "optimal": { "net_profit": 80.0, "win_rate": 0.52, "optimality_rate": 1.00 }
    }
  }
}
```

#### 10. `SPEED_UPDATED`
```json
{
  "event_type": "SPEED_UPDATED",
  "session_id": "sim-c5a4b123",
  "round_number": 3,
  "timestamp": "2026-10-12T21:40:05Z",
  "payload": { "delay_ms": 150.0 }
}
```
