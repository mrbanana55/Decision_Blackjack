"""Unit tests for agent fault handling and synchronous recovery (User Story 3)."""

import asyncio
from app.simulation import (
    BasicStrategyAgent,
    EventType,
    FakeJevAgent,
    FakeLayaAgent,
    SessionStatus,
    SimulationConfig,
    SimulationError,
    SimulationOrchestrator,
    SimulationStateError,
)


def test_agent_exception_triggers_fail_fast_pause_error():
    """Verify provider exception pauses all tables in PAUSED_ERROR immediately."""
    async def _test():
        config = SimulationConfig(session_id="fault-sim-1", seed=42, max_rounds=5)
        orchestrator = SimulationOrchestrator(config)

        t_opt = orchestrator.add_entity("opt", BasicStrategyAgent())
        t_jev = orchestrator.add_entity("jev", FakeJevAgent(simulated_latency_ms=0.0))

        # Inject error into Jev on round 1
        t_jev.provider.inject_fault()

        error_events = []
        orchestrator.event_bus.subscribe(
            EventType.SESSION_ERROR,
            lambda e: error_events.append(e),
        )

        sim_task = asyncio.create_task(orchestrator.start())
        await sim_task

        assert orchestrator.status == SessionStatus.PAUSED_ERROR
        assert orchestrator.failed_entity_id == "jev"
        assert orchestrator.last_error is not None
        assert len(error_events) == 1
        assert error_events[0].payload["entity_id"] == "jev"

        # Peer table state is preserved cleanly without corruption
        assert t_opt.current_bankroll is not None

        # Recovery via retry_failed_entity
        await orchestrator.retry_failed_entity("jev")
        assert orchestrator.status == SessionStatus.COMPLETED
        assert orchestrator.current_round == 5

    asyncio.run(_test())


def test_illegal_action_triggers_paused_error():
    """Verify illegal action is caught and halts in PAUSED_ERROR."""
    async def _test():
        config = SimulationConfig(session_id="fault-sim-2", seed=42, max_rounds=3)
        orchestrator = SimulationOrchestrator(config)

        t_opt = orchestrator.add_entity("opt", BasicStrategyAgent())
        t_laya = orchestrator.add_entity("laya", FakeLayaAgent(simulated_latency_ms=0.0))

        # Inject illegal action into Laya
        t_laya.provider.inject_illegal_action()

        await orchestrator.start()

        assert orchestrator.status == SessionStatus.PAUSED_ERROR
        assert orchestrator.failed_entity_id == "laya"
        assert "illegal" in str(orchestrator.last_error).lower()

        # Recovery via retry_failed_entity
        await orchestrator.retry_failed_entity("laya")
        assert orchestrator.status == SessionStatus.COMPLETED

    asyncio.run(_test())


def test_invalid_retry_guards():
    """Verify error conditions on retry_failed_entity."""
    async def _test():
        config = SimulationConfig(session_id="fault-sim-3", seed=42, max_rounds=2)
        orchestrator = SimulationOrchestrator(config)
        orchestrator.add_entity("opt", BasicStrategyAgent())

        # Cannot retry when not in PAUSED_ERROR
        try:
            await orchestrator.retry_failed_entity("opt")
            assert False, "Should have raised SimulationStateError"
        except SimulationStateError:
            pass

    asyncio.run(_test())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All fault handling tests passed!")
