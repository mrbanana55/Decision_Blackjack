"""Simulation integration tests verifying fault resilience, pause/resume, and telemetry streaming for JevAgent."""

from unittest.mock import AsyncMock

import pytest

from app.engine.types import Action
from app.integrations.jev.agent import JevAgent
from app.integrations.jev.schemas import ChoiceAnswer, SystemOneResponse, UsageInfo
from app.models.basic_strategy_player import BasicStrategyPlayer
from app.simulation.events import EventEmitter, EventType, SimulationEvent
from app.simulation.interfaces import AgentFaultError
from app.simulation.orchestrator import SimulationOrchestrator
from app.simulation.types import SessionStatus, SimulationConfig


@pytest.fixture
def base_config() -> SimulationConfig:
    return SimulationConfig(
        session_id="test-jev-fault-sim",
        seed=42,
        max_rounds=3,
        initial_bankroll=1000.0,
    )


@pytest.mark.asyncio
async def test_jev_fault_pauses_simulation_without_data_loss(base_config):
    """Verify that network timeout or rate limit error raises AgentFaultError and pauses session into PAUSED_ERROR."""
    mock_client = AsyncMock()
    mock_client.send_systemone = AsyncMock()

    async def side_effect(request):
        if "bet_sizing" in request.questions:
            return SystemOneResponse(
                model="jev-latest",
                answers={"bet_sizing": ChoiceAnswer(choice="1x", confidence=0.90)},
                meta={"latency_ms": 20.0},
            )
        raise AgentFaultError("TypeSafe API request timed out after 15.0s")

    mock_client.send_systemone.side_effect = side_effect

    jev_agent = JevAgent(client=mock_client)
    event_bus = EventEmitter()
    captured_errors: list[SimulationEvent] = []
    event_bus.subscribe(EventType.SESSION_ERROR, lambda e: captured_errors.append(e))

    orchestrator = SimulationOrchestrator(base_config, event_bus=event_bus)
    orchestrator.add_entity("jev", jev_agent)

    await orchestrator.start()

    # Assert orchestrator entered fault-paused status
    assert orchestrator.status == SessionStatus.PAUSED_ERROR
    assert orchestrator.failed_entity_id == "jev"
    assert orchestrator.last_error is not None
    assert "TypeSafe API request timed out" in str(orchestrator.last_error)

    # Verify error event was emitted
    assert len(captured_errors) == 1
    assert captured_errors[0].payload["entity_id"] == "jev"
    assert "TypeSafe API request timed out" in captured_errors[0].payload["error"]

    # Verify session state and table bankrolls are intact
    jev_table = orchestrator.tables["jev"]
    assert jev_table.current_bankroll > 0.0
    assert not jev_table.is_eliminated


@pytest.mark.asyncio
async def test_jev_fault_recovery_and_resume(base_config):
    """Verify that after resolving an API fault, resuming the simulation completes remaining rounds."""
    mock_client = AsyncMock()
    mock_client.send_systemone = AsyncMock()

    valid_decision_response = SystemOneResponse(
        model="jev-latest",
        answers={"action": ChoiceAnswer(choice="stand", confidence=0.95)},
        usage=UsageInfo(input_tokens=100, output_tokens=10),
        meta={"latency_ms": 25.0},
    )
    valid_bet_response = SystemOneResponse(
        model="jev-latest",
        answers={"bet_sizing": ChoiceAnswer(choice="1x", confidence=0.90)},
        meta={"latency_ms": 15.0},
    )

    should_fail = True

    async def side_effect(request):
        if "bet_sizing" in request.questions:
            return valid_bet_response
        if should_fail:
            raise AgentFaultError("Transient cloud 529 overload")
        return valid_decision_response

    mock_client.send_systemone.side_effect = side_effect

    jev_agent = JevAgent(client=mock_client)
    orchestrator = SimulationOrchestrator(base_config)
    orchestrator.add_entity("jev", jev_agent)

    await orchestrator.start()
    assert orchestrator.status == SessionStatus.PAUSED_ERROR

    # Recover fault and resume
    should_fail = False
    await orchestrator.resume()

    assert orchestrator.status == SessionStatus.COMPLETED
    assert orchestrator.current_round == base_config.max_rounds
    assert orchestrator.tables["jev"].rounds_played == base_config.max_rounds


@pytest.mark.asyncio
async def test_jev_multi_agent_simulation_and_comparator():
    """Verify Jev plays concurrently with BasicStrategy under round barrier and populates comparator telemetry."""
    config = SimulationConfig(
        session_id="test-jev-multi-agent",
        seed=100,
        max_rounds=2,
        initial_bankroll=1000.0,
    )

    mock_client = AsyncMock()
    mock_client.send_systemone = AsyncMock()

    async def side_effect(request):
        if "bet_sizing" in request.questions:
            return SystemOneResponse(
                model="jev-latest",
                answers={"bet_sizing": ChoiceAnswer(choice="1x", confidence=0.95)},
            )
        # Tactical choice
        return SystemOneResponse(
            model="jev-latest",
            answers={"action": ChoiceAnswer(choice="stand", confidence=0.90)},
            usage=UsageInfo(input_tokens=110, output_tokens=12),
            meta={"latency_ms": 30.0},
        )

    mock_client.send_systemone.side_effect = side_effect

    jev_agent = JevAgent(client=mock_client)
    basic_player = BasicStrategyPlayer()

    event_bus = EventEmitter()
    decisions_applied: list[SimulationEvent] = []
    event_bus.subscribe(
        EventType.DECISION_APPLIED, lambda e: decisions_applied.append(e)
    )

    orchestrator = SimulationOrchestrator(config, event_bus=event_bus)
    orchestrator.add_entity("jev", jev_agent)
    orchestrator.add_entity("optimal", basic_player)

    await orchestrator.start()

    assert orchestrator.status == SessionStatus.COMPLETED
    assert orchestrator.current_round == 2
    assert orchestrator.tables["jev"].rounds_played == 2
    assert orchestrator.tables["optimal"].rounds_played == 2

    # Verify decision comparator evaluation and metadata capture
    jev_events = [e for e in decisions_applied if e.payload.get("entity_id") == "jev"]
    assert len(jev_events) > 0
    for e in jev_events:
        assert e.payload["model_name"] == "jev-latest"
        assert e.payload["model_provider"] == "typesafe"
        assert "comparison" in e.payload
        comp = e.payload["comparison"]
        assert "is_optimal" in comp
        assert "optimal_action" in comp
