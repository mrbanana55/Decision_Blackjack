"""Validation tests executing the four scenarios defined in quickstart.md."""

import asyncio
from app.engine.rules import TableRules
from app.simulation import (
    BasicStrategyAgent,
    FakeJevAgent,
    FakeLayaAgent,
    SessionStatus,
    SimulationConfig,
    SimulationOrchestrator,
)


def test_quickstart_scenario_1_multi_agent():
    """Scenario 1: Multi-Agent Simulation with Fake Agents."""
    async def _test():
        config = SimulationConfig(
            session_id="sim-test-01",
            seed=12345,
            max_rounds=10,
            initial_bankroll=1000.0,
            table_rules=TableRules(min_bet=10.0, max_bet=500.0),
        )

        orchestrator = SimulationOrchestrator(config=config)
        orchestrator.add_entity(BasicStrategyAgent())
        orchestrator.add_entity(FakeJevAgent(simulated_latency_ms=1.0))
        orchestrator.add_entity(FakeLayaAgent(simulated_latency_ms=1.0))

        await orchestrator.start()
        assert orchestrator.status == SessionStatus.COMPLETED

        for entity_id, table in orchestrator.tables.items():
            assert table.rounds_played == 10
            assert table.current_bankroll > 0

    asyncio.run(_test())


def test_quickstart_scenario_2_pause_step_resume():
    """Scenario 2: Pause, Single-Step, and Resume Flow Control."""
    async def _test():
        orchestrator = SimulationOrchestrator(
            config=SimulationConfig(session_id="sim-flow-01", max_rounds=20, seed=42)
        )
        orchestrator.add_entity(FakeJevAgent(simulated_latency_ms=10.0))

        task = asyncio.create_task(orchestrator.start())
        await asyncio.sleep(0.02)

        await orchestrator.pause()
        assert orchestrator.status == SessionStatus.PAUSED
        current_round = orchestrator.session.current_round

        await orchestrator.step_round()
        assert orchestrator.session.current_round == current_round + 1
        assert orchestrator.status == SessionStatus.PAUSED

        await orchestrator.resume()
        await task
        assert orchestrator.status == SessionStatus.COMPLETED

    asyncio.run(_test())


def test_quickstart_scenario_3_error_recovery():
    """Scenario 3: Agent Error Handling & Synchronous Recovery."""
    async def _test():
        failing_jev = FakeJevAgent(fail_on_round=3, simulated_latency_ms=0.0)

        orchestrator = SimulationOrchestrator(
            config=SimulationConfig(session_id="sim-err-01", max_rounds=5, seed=42)
        )
        orchestrator.add_entity(failing_jev)

        await orchestrator.start()

        assert orchestrator.status == SessionStatus.PAUSED_ERROR
        assert orchestrator.session.current_round == 3

        failing_jev.clear_fault()
        await orchestrator.retry_failed_entity(entity_id="jev")

        assert orchestrator.status == SessionStatus.COMPLETED
        assert orchestrator.session.current_round == 5

    asyncio.run(_test())


def test_quickstart_scenario_4_generational_shoe_pool():
    """Scenario 4: Generational Shoe Pool Validation."""
    async def _test():
        rules = TableRules(penetration=0.3, num_decks=1)
        orchestrator = SimulationOrchestrator(
            config=SimulationConfig(max_rounds=30, seed=999, table_rules=rules)
        )
        orchestrator.add_entity(BasicStrategyAgent())
        orchestrator.add_entity(FakeJevAgent(simulated_latency_ms=0.0))

        await orchestrator.start()

        shoe_pool = orchestrator.shoe_pool
        assert len(shoe_pool.generation_cache) > 1

    asyncio.run(_test())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All quickstart validation scenarios passed!")
