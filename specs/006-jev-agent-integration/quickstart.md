# Quickstart & Verification Guide: Jev Decision Agent Integration

**Feature**: `006-jev-agent-integration`  
**Status**: Ready for Implementation  

This guide provides end-to-end verification workflows to validate Jev credential configuration, situational schema generation, in-hand decision resolution, and orchestrator simulation runs.

---

## 1. Prerequisites

1. **Environment Variables**: Verify `.env` contains valid TypeSafe configuration:
   ```env
   TYPESAFE_API_URL=https://api.typesafe.ai/v1/systemone
   TYPESAFE_API_KEY=apikey_2118223dd88583f2493fbcd292a863d13918_...
   TYPESAFE_MODEL=jev-latest
   ```
2. **Backend Container**: Ensure backend and database containers are up and running:
   ```bash
   docker compose up -d backend db
   ```

---

## 2. Verification Workflows

### Scenario 1: Diagnostic Health Probe (`/health/jev`)
Verify that the backend service correctly loads the API key and validates connectivity:

```bash
docker compose exec backend uv run python -c "
import asyncio
from app.integrations.jev import JevClient, JevConfig

async def test():
    config = JevConfig()
    async with JevClient(config) as client:
        health = await client.check_health()
        print('Jev Health Status:', health.status, '| Model:', health.model, '| Key Present:', health.has_api_key)

asyncio.run(test())
"
```
**Expected Outcome**: Output displays `Jev Health Status: ok | Model: jev-latest | Key Present: True`.

---

### Scenario 2: Situational Schema Construction Verification
Verify that `JevSchemaBuilder` dynamically generates the exact criteria matching each situation without hardcoded values:

```bash
docker compose exec backend uv run pytest tests/test_jev_schemas.py -v
```
**Expected Outcome**:
- `test_paired_hand_includes_split`: Verifies 8-8 includes `split` and `hit`/`stand`.
- `test_multi_card_hand_excludes_split_double_surrender`: Verifies 3-card hand has strictly `hit` and `stand`.
- `test_surrender_respects_table_rules`: Verifies surrender appears only when allowed by table rules.
- `test_dynamic_minimum_bet_scaling`: Verifies round betting criteria uses configured table minimum bet (e.g. $25 or $100).

---

### Scenario 3: Real or Mock System One Inference
Verify that `JevClient` dispatches a valid TypeSafe System One request with Bearer authorization and maps the response:

```bash
docker compose exec backend uv run pytest tests/test_jev_client.py -v
```
**Expected Outcome**: Test sends `SystemOneRequest`, measures latency, and returns parsed `SystemOneResponse` with choice selection, probabilities distribution, and token usage.

---

### Scenario 4: Full Multi-Round Simulation with Jev Entity
Execute an end-to-end simulation where Jev plays alongside Laya and Optimal Basic Strategy:

```bash
docker compose exec backend uv run python -c "
import asyncio
from app.simulation import SimulationOrchestrator, SimulationConfig
from app.integrations.jev import JevAgent

async def run_sim():
    config = SimulationConfig(max_rounds=5, seed=42)
    orchestrator = SimulationOrchestrator(config)
    orchestrator.add_entity('jev_player', JevAgent())
    session = await orchestrator.run()
    print('Completed rounds:', session.rounds_completed)

asyncio.run(run_sim())
"
```
**Expected Outcome**: 5 rounds complete cleanly, with Jev selecting valid actions at every turn and telemetry recorded to PostgreSQL persistence.

---

## 3. Full Test Suite Execution

Run all Jev integration test suites and verify static typing inside Docker:
```bash
docker compose exec backend uv run pytest tests/test_jev_*.py
docker compose exec backend uv run ruff check app/integrations/jev tests/test_jev_*.py
```
