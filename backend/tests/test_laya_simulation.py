"""Simulation integration tests verifying fault resilience, pause/resume, and telemetry streaming for LayaAgent."""

from unittest.mock import AsyncMock

import pytest

from app.engine.types import Action
from app.integrations.laya.agent import LayaAgent
from app.integrations.laya.schemas import ChoiceAnswer, SystemOneResponse
from app.simulation.events import EventEmitter, EventType, SimulationEvent
from app.simulation.interfaces import AgentFaultError
from app.simulation.orchestrator import SimulationOrchestrator
from app.simulation.types import SessionStatus, SimulationConfig


@pytest.fixture
def base_config() -> SimulationConfig:
    return SimulationConfig(
        session_id="test-laya-fault-sim",
        seed=42,
        max_rounds=3,
        initial_bankroll=1000.0,
    )


@pytest.mark.asyncio
async def test_laya_fault_pauses_simulation_without_data_loss(base_config):
    """Verify that host disconnect or Laya timeout raises AgentFaultError and pauses session into PAUSED_ERROR."""
    mock_client = AsyncMock()
    mock_client.send_systemone = AsyncMock()

    async def side_effect(request):
        if "bet_sizing" in request.questions:
            return SystemOneResponse(
                answers={"bet_sizing": ChoiceAnswer(choice="1x", confidence=0.90)},
                meta={"latency_ms": 20.0, "device": "mps"},
            )
        raise AgentFaultError("Host connection to Laya timed out after 3.0s")

    mock_client.send_systemone.side_effect = side_effect

    laya_agent = LayaAgent(client=mock_client)
    event_bus = EventEmitter()
    captured_errors: list[SimulationEvent] = []
    event_bus.subscribe(EventType.SESSION_ERROR, lambda e: captured_errors.append(e))

    orchestrator = SimulationOrchestrator(base_config, event_bus=event_bus)
    orchestrator.add_entity("laya", laya_agent)

    await orchestrator.start()

    # Assert orchestrator entered fault-paused status
    assert orchestrator.status == SessionStatus.PAUSED_ERROR
    assert orchestrator.failed_entity_id == "laya"
    assert orchestrator.last_error is not None
    assert "Host connection to Laya timed out" in str(orchestrator.last_error)

    # Verify error event was emitted
    assert len(captured_errors) == 1
    assert captured_errors[0].payload["entity_id"] == "laya"
    assert "Host connection to Laya timed out" in captured_errors[0].payload["error"]

    # Verify session state and table bankrolls are intact
    laya_table = orchestrator.tables["laya"]
    assert laya_table.current_bankroll > 0.0
    assert not laya_table.is_eliminated


@pytest.mark.asyncio
async def test_laya_fault_recovery_and_resume(base_config):
    """Verify that after resolving a host fault, resuming the simulation successfully completes remaining rounds."""
    mock_client = AsyncMock()
    mock_client.send_systemone = AsyncMock()

    valid_decision_response = SystemOneResponse(
        answers={"action": ChoiceAnswer(choice="stand", confidence=0.95)},
        meta={"model": "typed-decisions", "device": "mps", "latency_ms": 18.0},
    )
    valid_bet_response = SystemOneResponse(
        answers={"bet_sizing": ChoiceAnswer(choice="1x", confidence=0.90)},
        meta={"latency_ms": 15.0},
    )

    should_fail = True

    async def side_effect(request):
        if "bet_sizing" in request.questions:
            return valid_bet_response
        if should_fail:
            raise AgentFaultError("Connection refused by host")
        return valid_decision_response

    mock_client.send_systemone.side_effect = side_effect

    laya_agent = LayaAgent(client=mock_client)
    orchestrator = SimulationOrchestrator(base_config)
    orchestrator.add_entity("laya", laya_agent)

    await orchestrator.start()
    assert orchestrator.status == SessionStatus.PAUSED_ERROR

    # Step 2: Recover client service with valid decisions
    should_fail = False

    # Resume the orchestrator
    await orchestrator.resume()

    assert orchestrator.status == SessionStatus.COMPLETED
    assert orchestrator.current_round == base_config.max_rounds
    assert orchestrator.tables["laya"].rounds_played == base_config.max_rounds


@pytest.mark.asyncio
async def test_laya_simulation_telemetry_and_comparator(base_config):
    """Verify that Laya decisions emit DECISION_APPLIED with telemetry metadata and DecisionComparator oracle."""
    mock_client = AsyncMock()
    # Mock betting response
    mock_bet = SystemOneResponse(
        answers={"bet_sizing": ChoiceAnswer(choice="2x", confidence=0.88)},
        meta={"model": "typed-decisions", "device": "mps", "latency_ms": 25.0},
    )
    # Mock hand action response
    mock_action = SystemOneResponse(
        answers={"action": ChoiceAnswer(choice="hit", confidence=0.92, distribution={"hit": 0.92, "stand": 0.08})},
        meta={"model": "typed-decisions", "device": "mps", "latency_ms": 28.5},
    )

    async def side_effect(request):
        if "bet_sizing" in request.questions:
            return mock_bet
        return mock_action

    mock_client.send_systemone.side_effect = side_effect

    event_bus = EventEmitter()
    captured_decisions: list[SimulationEvent] = []
    event_bus.subscribe(EventType.DECISION_APPLIED, lambda e: captured_decisions.append(e))

    cfg = SimulationConfig(
        session_id="test-telemetry-sim",
        seed=100,
        max_rounds=1,
        initial_bankroll=1000.0,
    )
    orchestrator = SimulationOrchestrator(cfg, event_bus=event_bus)
    laya_agent = LayaAgent(client=mock_client)
    orchestrator.add_entity("laya", laya_agent)

    await orchestrator.start()

    assert len(captured_decisions) >= 1
    event = captured_decisions[0]
    payload = event.payload

    # Validate decision payload structure
    assert payload["entity_id"] == "laya"
    assert payload["action"] in [a.value for a in Action]
    assert payload["confidence"] == 0.92
    assert payload["latency_ms"] > 0.0

    # Validate attached telemetry metadata
    assert "metadata" in payload
    assert payload["metadata"]["provider"] == "laya"
    assert payload["metadata"]["device"] == "mps"
    assert payload["model_name"] == "typed-decisions"

    # Validate attached DecisionComparator oracle benchmark
    assert "comparison" in payload
    comparison = payload["comparison"]
    assert "is_optimal" in comparison
    assert "optimal_action" in comparison
    assert "category" in comparison
