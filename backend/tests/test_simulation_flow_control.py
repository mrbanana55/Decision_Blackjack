"""Unit tests for simulation execution flow control (pause, resume, step, stop)."""

import asyncio
from app.engine.types import RoundPhase
from app.simulation import (
    BasicStrategyAgent,
    FakeJevAgent,
    SessionStatus,
    SimulationConfig,
    SimulationOrchestrator,
)


def test_step_round():
    """Verify step_round advances exactly one round at a time and stays paused."""
    async def _test():
        config = SimulationConfig(session_id="step-round-sim", seed=42, max_rounds=5)
        orchestrator = SimulationOrchestrator(config)
        orchestrator.add_entity("opt", BasicStrategyAgent())

        assert orchestrator.status == SessionStatus.INITIALIZING
        assert orchestrator.current_round == 0

        # Step Round 1
        await orchestrator.step_round()
        assert orchestrator.status == SessionStatus.PAUSED
        assert orchestrator.current_round == 1
        assert orchestrator.tables["opt"].rounds_played == 1

        # Step Round 2
        await orchestrator.step_round()
        assert orchestrator.status == SessionStatus.PAUSED
        assert orchestrator.current_round == 2
        assert orchestrator.tables["opt"].rounds_played == 2

    asyncio.run(_test())


def test_step_turn_preserves_in_flight_hand():
    """Verify step_turn advances a single decision turn and suspends mid-round."""
    async def _test():
        config = SimulationConfig(session_id="step-turn-sim", seed=42, max_rounds=5)
        orchestrator = SimulationOrchestrator(config)
        orchestrator.add_entity("opt", BasicStrategyAgent())

        # Step a single turn
        await orchestrator.step_turn()
        assert orchestrator.status == SessionStatus.PAUSED
        assert orchestrator.current_round >= 1
        table = orchestrator.tables["opt"]
        assert len(table.round_engine.player_hands) > 0
        assert table.phase == RoundPhase.PLAYER_TURNS

    asyncio.run(_test())


def test_pause_and_resume():
    """Verify pause cleanly suspends execution and resume completes remaining rounds."""
    async def _test():
        config = SimulationConfig(session_id="pause-resume-sim", seed=42, max_rounds=6)
        orchestrator = SimulationOrchestrator(config)
        # Use small latency so background task is in-flight
        orchestrator.add_entity("jev", FakeJevAgent(simulated_latency_ms=10.0))

        sim_task = asyncio.create_task(orchestrator.start())

        # Let it run a bit
        await asyncio.sleep(0.02)

        # Pause
        await orchestrator.pause()
        assert orchestrator.status == SessionStatus.PAUSED
        paused_round = orchestrator.current_round

        # Ensure it remains paused
        await asyncio.sleep(0.03)
        assert orchestrator.status == SessionStatus.PAUSED

        # Resume
        await orchestrator.resume()
        await sim_task

        assert orchestrator.status == SessionStatus.COMPLETED
        assert orchestrator.current_round == 6
        assert orchestrator.tables["jev"].rounds_played == 6

    asyncio.run(_test())


def test_stop_cancels_execution():
    """Verify stop transitions to STOPPED and finalizes session metrics."""
    async def _test():
        config = SimulationConfig(session_id="stop-sim", seed=42, max_rounds=20)
        orchestrator = SimulationOrchestrator(config)
        orchestrator.add_entity("opt", BasicStrategyAgent())

        # Step 2 rounds
        await orchestrator.step_round()
        await orchestrator.step_round()
        assert orchestrator.current_round == 2

        # Stop
        await orchestrator.stop()
        assert orchestrator.status == SessionStatus.STOPPED
        assert orchestrator.session.end_time is not None
        assert orchestrator.session.status == SessionStatus.STOPPED

    asyncio.run(_test())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All flow control tests passed!")
