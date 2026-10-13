# Quickstart Validation Guide: Simulation Frontend API

**Feature**: `007-simulation-frontend-api`  
**Date**: 2026-10-12  
**Status**: Ready for Implementation  

This guide provides runnable scenarios to validate the Simulation Frontend API, WebSocket telemetry streaming, data exporters, and database purge operations end-to-end.

---

## 1. Prerequisites & Environment

Ensure containers are running or dependencies are installed locally:

```bash
# Docker Compose environment
docker compose up -d db backend
```

Verify backend health:
```bash
curl -s http://localhost:8000/health | jq .
```
Expected output:
```json
{
  "status": "ok",
  "service": "backend",
  "environment": "development"
}
```

---

## 2. Validation Scenarios

### Scenario 1: Provision Simulation with Custom House Rules

Submit a configuration defining rounds, participating players, and custom table rules matching [`Reglas de BlackJack.md`](../../docs/Reglas%20de%20BlackJack.md):

```bash
curl -X POST http://localhost:8000/api/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "max_rounds": 5,
    "num_simulations": 1,
    "execution_mode": "visualized",
    "delay_ms": 200.0,
    "seed": 42,
    "entities": ["optimal", "jev", "laya"],
    "mock_mode": true,
    "table_rules": {
      "soft_17_rule": "S17",
      "blackjack_payout": 1.5,
      "hole_card_rule": "AMERICAN_PEEK",
      "insurance_allowed": true,
      "surrender_rule": "LATE",
      "double_after_split": true,
      "max_split_hands": 4,
      "resplit_aces": false,
      "num_decks": 6,
      "penetration": 0.75,
      "initial_bankroll": 1000.0,
      "min_bet": 10.0,
      "max_bet": 500.0
    }
  }' | jq .
```

**Expected Outcome**: Returns HTTP `201 Created` with a `session_id`, `run_id`, `status: "INITIALIZING"`, and `websocket_url`.

---

### Scenario 2: Stream Live Telemetry Over WebSocket

Connect a WebSocket client to observe turn-by-turn decisions, real-time strategy deviations from Basic Strategy, and running category metrics:

```python
# test_ws.py
import asyncio
import json
import websockets

async def watch_simulation(session_id: str):
    uri = f"ws://localhost:8000/ws/simulations/{session_id}"
    async with websockets.connect(uri) as ws:
        print(f"Connected to {uri}")
        async for message in ws:
            data = json.loads(message)
            event_type = data.get("event_type")
            round_num = data.get("round_number")
            
            if event_type == "DECISION_MADE":
                payload = data["payload"]
                comp = payload.get("comparison", {})
                is_opt = comp.get("is_optimal", True)
                opt_action = comp.get("optimal_action", payload["action"])
                cat = comp.get("category", "unknown")
                status_str = "OPTIMAL" if is_opt else f"DEVIATION (Optimal: {opt_action}, Cat: {cat})"
                print(f"[Round {round_num}] Entity: {payload['entity_id']} -> Action: {payload['action']} "
                      f"[{status_str}] (Conf: {payload['confidence']:.2f})")
            elif event_type == "ROUND_SETTLED":
                print(f"[Round {round_num}] Round Settled. Dealer total: {data['payload']['dealer_total']}")
                running_dev = data["payload"].get("running_deviations", {})
                for ent, dev in running_dev.items():
                    print(f"  -> {ent}: {dev['deviations_count']} deviations / {dev['total_decisions']} decisions "
                          f"({dev['optimality_rate']*100:.1f}% optimal)")
            elif event_type == "SESSION_COMPLETED":
                print("Simulation completed successfully!")
                break

# Run with a valid session_id
asyncio.run(watch_simulation("<SESSION_ID>"))
```

Query the dedicated deviation analytics endpoint via REST at any point:
```bash
curl -s http://localhost:8000/api/simulations/<SESSION_ID>/deviations | jq .
```

**Expected Outcome**: Receives synchronized `DECISION_MADE` events containing rich strategy comparisons, live running deviation tallies per round settlement, and full category-segmented deviation statistics over REST.

---

### Scenario 3: Interactive Flow Control & Dynamic Speed Adjustment

Send client commands over the open WebSocket to pause, adjust speed, and resume:

```python
# Send over active WebSocket connection:
await ws.send(json.dumps({"command": "pause"}))
# Server responds with SESSION_PAUSED event frame

await ws.send(json.dumps({"command": "set_speed", "delay_ms": 50.0}))
# Server responds with SPEED_UPDATED event frame

await ws.send(json.dumps({"command": "resume"}))
# Server responds with SESSION_RESUMED and continues execution
```

**Expected Outcome**: Simulation pauses cleanly at the turn boundary and resumes execution with updated pacing delay.

---

### Scenario 4: Export Single Simulation JSON Artifact

Export the complete hierarchical history of a specific simulation:

```bash
curl -s -O -J "http://localhost:8000/api/export/simulations/<SESSION_OR_RUN_ID>"
```

**Expected Outcome**: Downloads `simulation_<ID>_export.json` containing run metadata, player benchmarks, shoe reshuffle events, and round-by-round hands and decisions.

---

### Scenario 5: Export Full Database JSON Archive

Export all historical runs and aggregate metrics across the entire database:

```bash
curl -s -O -J "http://localhost:8000/api/export/database"
```

**Expected Outcome**: Downloads `decision_blackjack_full_export_<TIMESTAMP>.json` with complete relational run history.

---

### Scenario 6: Reset / Clear Database

Purge all records across all 15 tables when no simulations are actively running:

```bash
curl -X DELETE http://localhost:8000/api/database | jq .
```

**Expected Outcome**:
```json
{
  "status": "cleared",
  "tables_purged": 15,
  "cleared_tables": [
    "runs", "configurations", "simulations", "player_sessions", "shoes",
    "player_shoe_states", "rounds", "round_players", "hands", "card_events",
    "bets", "bankroll_transactions", "hand_results", "decisions", "model_responses"
  ],
  "timestamp": "2026-10-12T21:45:00Z"
}
```

When queried again, `GET /api/simulations` returns `{ "items": [], "total": 0 }`.

---

## 3. Automated Test Suite Execution

Run all API and WebSocket integration tests inside the backend virtual environment:

```bash
backend/.venv/bin/pytest backend/tests/test_api_*.py -v
```

**Expected Outcome**: All route tests (configuration, flow control, WebSocket streaming, JSON exports, database reset) pass cleanly.
