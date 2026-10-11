"""Unit tests for simulation telemetry and event broadcasting (User Story 5)."""

import asyncio
from datetime import datetime
from app.simulation import (
    BasicStrategyAgent,
    EventType,
    FakeJevAgent,
    SessionStatus,
    SimulationConfig,
    SimulationOrchestrator,
)


def test_telemetry_event_stream_and_schema():
    """Verify strongly typed event emission across an entire simulation run."""
    async def _test():
        config = SimulationConfig(
            session_id="telemetry-sim-test",
            seed=42,
            max_rounds=3,
            initial_bankroll=1000.0,
        )
        orchestrator = SimulationOrchestrator(config)
        orchestrator.add_entity("opt", BasicStrategyAgent())

        emitted_events = []
        orchestrator.event_bus.subscribe(None, lambda e: emitted_events.append(e))

        await orchestrator.start()

        assert orchestrator.status == SessionStatus.COMPLETED
        assert len(emitted_events) > 0

        # Check first event is SESSION_STARTED
        first = emitted_events[0]
        assert first.event_type == EventType.SESSION_STARTED
        assert first.session_id == "telemetry-sim-test"
        assert first.event_id.startswith("evt-")
        # Validate ISO timestamp
        dt = datetime.fromisoformat(first.timestamp)
        assert dt is not None
        assert "entities" in first.payload

        # Check last event is SESSION_COMPLETED
        last = emitted_events[-1]
        assert last.event_type == EventType.SESSION_COMPLETED
        assert last.payload["total_rounds"] == 3
        assert "metrics" in last.payload

        # Check for ROUND_STARTED and ROUND_SETTLED events
        event_types = [e.event_type for e in emitted_events]
        assert EventType.ROUND_STARTED in event_types
        assert EventType.CARD_DEALT in event_types
        assert EventType.ROUND_SETTLED in event_types

        # Verify DECISION_APPLIED schema
        decision_events = [e for e in emitted_events if e.event_type == EventType.DECISION_APPLIED]
        if decision_events:
            d_evt = decision_events[0]
            assert "action" in d_evt.payload
            assert "confidence" in d_evt.payload
            assert "latency_ms" in d_evt.payload
            assert "reasoning" in d_evt.payload

        # Verify chronological ordering of rounds
        round_started_rounds = [
            e.payload["round_number"]
            for e in emitted_events
            if e.event_type == EventType.ROUND_STARTED
        ]
        assert round_started_rounds == [1, 2, 3]

    asyncio.run(_test())


def test_telemetry_flow_control_events():
    """Verify pause, resume, and stop milestones emit proper telemetry."""
    async def _test():
        config = SimulationConfig(session_id="fc-telemetry-sim", seed=42, max_rounds=5)
        orchestrator = SimulationOrchestrator(config)
        orchestrator.add_entity("opt", BasicStrategyAgent())

        history = []
        orchestrator.event_bus.subscribe(None, lambda e: history.append(e.event_type))

        await orchestrator.step_round()
        assert EventType.ROUND_STARTED in history
        assert EventType.SESSION_PAUSED in history

        await orchestrator.resume()
        assert EventType.SESSION_RESUMED in history
        assert EventType.SESSION_COMPLETED in history

    asyncio.run(_test())


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
            print(f"✓ {name}")
    print("All telemetry tests passed!")
