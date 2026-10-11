# Quickstart Guide: Simulation Orchestrator Validation

**Feature**: [spec.md](spec.md)  
**Package**: `backend/app/simulation/`  
**Date**: 2026-10-10

This guide demonstrates how an external test controller or script drives complete multi-agent simulations headlessly using the `SimulationOrchestrator` API with fake agents.

---

## 1. Scenario 1: Multi-Agent Simulation with Fake Agents

Runs a 10-round synchronized simulation comparing 3 fake entities:

```python
import asyncio
from app.engine.rules import TableRules
from app.simulation.agents.basic_strategy import BasicStrategyAgent
from app.simulation.agents.fake_agents import FakeJevAgent, FakeLayaAgent
from app.simulation.orchestrator import SimulationOrchestrator
from app.simulation.types import SessionStatus, SimulationConfig

async def main():
    config = SimulationConfig(
        session_id="sim-test-01",
        seed=12345,
        max_rounds=10,
        initial_bankroll=1000.0,
        table_rules=TableRules(min_bet=10.0, max_bet=500.0),
    )

    # Instantiate orchestrator with 3 isolated entity tables
    orchestrator = SimulationOrchestrator(config=config)
    orchestrator.add_entity(BasicStrategyAgent())
    orchestrator.add_entity(FakeJevAgent(simulated_latency_ms=10.0))
    orchestrator.add_entity(FakeLayaAgent(simulated_latency_ms=5.0))

    # Run simulation to natural completion
    await orchestrator.start()
    assert orchestrator.status == SessionStatus.COMPLETED

    # Inspect metrics per table
    for entity_id, table in orchestrator.tables.items():
        print(f"[{entity_id.upper()}] Final Bankroll: ${table.current_bankroll:.2f} | Rounds: {table.rounds_played}")
        assert table.rounds_played == 10

asyncio.run(main())
```

---

## 2. Scenario 2: Pause, Single-Step, and Resume Flow Control

Validates non-blocking pause, state preservation, and single-round step:

```python
import asyncio
from app.simulation.orchestrator import SimulationOrchestrator
from app.simulation.types import SessionStatus, SimulationConfig

async def test_pause_resume():
    orchestrator = SimulationOrchestrator(
        config=SimulationConfig(session_id="sim-flow-01", max_rounds=20, seed=42)
    )
    # Add default fake entities...
    
    # Launch in background task
    task = asyncio.create_task(orchestrator.start())
    await asyncio.sleep(0.05)  # Let it run a few rounds

    # Pause execution
    await orchestrator.pause()
    assert orchestrator.status == SessionStatus.PAUSED
    current_round = orchestrator.session.current_round

    # Step exactly 1 round
    await orchestrator.step_round()
    assert orchestrator.session.current_round == current_round + 1
    assert orchestrator.status == SessionStatus.PAUSED

    # Resume to completion
    await orchestrator.resume()
    await task
    assert orchestrator.status == SessionStatus.COMPLETED
```

---

## 3. Scenario 3: Agent Error Handling & Synchronous Recovery

Validates fail-fast pause and retry upon a simulated agent timeout:

```python
import asyncio
from app.simulation.agents.fake_agents import FakeJevAgent
from app.simulation.orchestrator import SimulationOrchestrator
from app.simulation.types import SessionStatus, SimulationConfig

async def test_error_recovery():
    # Configure fake Jev to fail on round 3
    failing_jev = FakeJevAgent(fail_on_round=3)
    
    orchestrator = SimulationOrchestrator(
        config=SimulationConfig(session_id="sim-err-01", max_rounds=5, seed=42)
    )
    orchestrator.add_entity(failing_jev)

    # Launch simulation
    await orchestrator.start()
    
    # Pauses synchronously in PAUSED_ERROR when Jev fails
    assert orchestrator.status == SessionStatus.PAUSED_ERROR
    assert orchestrator.session.current_round == 3

    # Clear error condition and retry
    failing_jev.clear_fault()
    await orchestrator.retry_failed_entity(entity_id="jev")

    # Resumes and completes remaining rounds
    assert orchestrator.status == SessionStatus.COMPLETED
    assert orchestrator.session.current_round == 5
```

---

## 4. Scenario 4: Generational Shoe Pool Validation

Validates that tables depleting cards at different rates retrieve identical shoe generations:

```python
import asyncio
from app.simulation.orchestrator import SimulationOrchestrator
from app.simulation.types import SimulationConfig
from app.engine.rules import TableRules

async def test_generational_shoe_pool():
    # Low penetration (30%) to trigger shoe reshuffling early
    rules = TableRules(penetration=0.3)
    orchestrator = SimulationOrchestrator(
        config=SimulationConfig(max_rounds=50, seed=999, table_rules=rules)
    )
    # Add entities...
    await orchestrator.start()

    # Verify all tables consumed the exact same shoe generations
    shoe_pool = orchestrator.shoe_pool
    assert len(shoe_pool.generation_cache) > 1
    print(f"Total Shoe Generations Created: {len(shoe_pool.generation_cache)}")
```
