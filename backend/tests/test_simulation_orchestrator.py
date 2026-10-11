"""Unit tests for SimulationOrchestrator (User Story 1 - Multi-Agent Simulation MVP)."""

import asyncio
from app.simulation import (
    BasicStrategyAgent,
    FakeJevAgent,
    FakeLayaAgent,
    OrchestratorController,
    SessionStatus,
    SimulationConfig,
    SimulationOrchestrator,
)


def test_orchestrator_conforms_to_controller_protocol():
    config = SimulationConfig(session_id="test-protocol-sim", seed=42, max_rounds=5)
    orchestrator = SimulationOrchestrator(config)
    assert isinstance(orchestrator, OrchestratorController)
    assert orchestrator.status == SessionStatus.INITIALIZING


def test_orchestrator_registers_entities_with_identical_initial_conditions():
    config = SimulationConfig(session_id="test-init-sim", seed=42, max_rounds=5, initial_bankroll=1000.0)
    orchestrator = SimulationOrchestrator(config)

    t_opt = orchestrator.add_entity("optimal", BasicStrategyAgent())
    t_jev = orchestrator.add_entity("jev", FakeJevAgent(simulated_latency_ms=0.0))
    t_laya = orchestrator.add_entity("laya", FakeLayaAgent(simulated_latency_ms=0.0))

    assert len(orchestrator.tables) == 3
    assert t_opt.current_bankroll == 1000.0
    assert t_jev.current_bankroll == 1000.0
    assert t_laya.current_bankroll == 1000.0

    # Guarantee identical initial cards in generation 0 shoe across tables
    cards_opt = [c for c in t_opt.round_engine.shoe.cards]
    cards_jev = [c for c in t_jev.round_engine.shoe.cards]
    cards_laya = [c for c in t_laya.round_engine.shoe.cards]
    assert cards_opt == cards_jev == cards_laya


def test_mvp_multi_agent_simulation_run():
    """Execute 10 complete synchronized rounds with 3 agents headlessly (US1 MVP)."""
    async def _test():
        config = SimulationConfig(
            session_id="mvp-sim-10-rounds",
            seed=42,
            max_rounds=10,
            initial_bankroll=1000.0,
        )
        orchestrator = SimulationOrchestrator(config)

        orchestrator.add_entity("optimal", BasicStrategyAgent())
        orchestrator.add_entity("jev", FakeJevAgent(simulated_latency_ms=1.0))
        orchestrator.add_entity("laya", FakeLayaAgent(simulated_latency_ms=1.0))

        await orchestrator.start()

        assert orchestrator.status == SessionStatus.COMPLETED
        assert orchestrator.current_round == 10

        session = orchestrator.session
        assert session.status == SessionStatus.COMPLETED
        assert session.current_round == 10
        assert len(session.metrics) == 3

        for entity_id in ("optimal", "jev", "laya"):
            m = session.metrics[entity_id]
            assert m.rounds_played == 10
            assert m.wins + m.losses + m.pushes >= 10
            assert m.starting_bankroll == 1000.0

    asyncio.run(_test())


def test_reproducibility_across_identical_seeds():
    """Verify that runs with identical seed and agents produce 100% identical results."""
    async def _run(seed: int) -> dict[str, float]:
        config = SimulationConfig(
            session_id=f"rep-sim-{seed}",
            seed=seed,
            max_rounds=5,
            initial_bankroll=1000.0,
        )
        orchestrator = SimulationOrchestrator(config)
        orchestrator.add_entity("opt", BasicStrategyAgent())
        orchestrator.add_entity("jev", FakeJevAgent(simulated_latency_ms=0.0))
        await orchestrator.start()
        return {eid: t.current_bankroll for eid, t in orchestrator.tables.items()}

    async def _test():
        results1 = await _run(12345)
        results2 = await _run(12345)
        assert results1 == results2

    asyncio.run(_test())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All orchestrator MVP tests passed!")
