# Quickstart & Verification Guide: Laya Decision Agent Integration

**Feature**: `005-laya-agent-integration`
**Status**: Ready for Implementation

This guide provides end-to-end verification workflows to validate Laya connectivity, situational schema generation, in-hand decision resolution, and orchestrator simulation runs.

---

## 1. Prerequisites

1. **Host Laya Server**: Ensure your local Laya server is active on your machine:
   ```bash
   curl http://127.0.0.1:1234/health
   # Expected response: {"status":"ok","loaded":["english","multilingual","typed-decisions"], ...}
   ```
2. **Environment Variable**: Check `.env` contains:
   ```env
   LAYA_BASE_URL=http://127.0.0.1:1234
   ```
3. **Backend Container**: Ensure backend container is up and running:
   ```bash
   docker compose up -d backend db
   ```

---

## 2. Verification Workflows

### Scenario 1: Container-to-Host Health Connectivity Probe
Verify that the backend container can reach the host machine's port 1234:

```bash
docker compose exec backend uv run python -c "
import asyncio
from app.integrations.laya import LayaClient, LayaConfig

async def test():
    config = LayaConfig()
    async with LayaClient(config) as client:
        health = await client.check_health()
        print('Laya Health Status:', health.status, '| Device:', health.device)

asyncio.run(test())
"
```
**Expected Outcome**: Output displays `Laya Health Status: ok | Device: mps` (or `cpu`).

---

### Scenario 2: Situational Schema Construction Verification
Verify that `LayaSchemaBuilder` dynamically generates the exact criteria matching each situation without hardcoded values:

```bash
docker compose exec backend uv run pytest tests/test_laya_schemas.py -v
```
**Expected Outcome**:
- `test_paired_hand_includes_split`: Verifies 8-8 includes `split` and `hit`/`stand`.
- `test_multi_card_hand_excludes_split_double_surrender`: Verifies 3-card hand has strictly `hit` and `stand`.
- `test_surrender_respects_table_rules`: Verifies surrender appears only when `table_rules.allow_late_surrender` is True.
- `test_dynamic_minimum_bet_scaling`: Verifies round betting criteria uses configured table minimum bet (e.g. $25 or $100), never hardcoded $50.

---

### Scenario 3: Real or Mock System One Inference
Verify that `LayaClient` dispatches a valid TypeSafe System One request and maps the response:

```bash
docker compose exec backend uv run pytest tests/test_laya_client.py -v
```
**Expected Outcome**: Test sends `SystemOneRequest`, measures sub-300ms latency, and returns parsed `SystemOneResponse` with choice selection and confidence distribution.

---

### Scenario 4: Full Multi-Round Simulation with Laya Entity
Execute an end-to-end simulation where Laya plays alongside the mathematical Basic Strategy baseline:

```bash
docker compose exec backend uv run python -c "
import asyncio
from app.simulation import SimulationOrchestrator, SimulationConfig
from app.integrations.laya import LayaAgent

async def run_sim():
    config = SimulationConfig(max_rounds=5, seed=42)
    orchestrator = SimulationOrchestrator(config)
    orchestrator.register_entity('laya_player', LayaAgent())
    session = await orchestrator.run()
    print('Completed rounds:', session.rounds_completed)

asyncio.run(run_sim())
"
```
**Expected Outcome**: 5 rounds complete cleanly, with Laya selecting valid actions at every turn and telemetry recorded to PostgreSQL persistence.

---

## 3. Full Test Suite Execution

Run all Laya integration test suites inside Docker:
```bash
docker compose exec backend uv run pytest tests/test_laya_*.py
docker compose exec backend uv run ruff check app/integrations/laya tests/test_laya_*.py
```
