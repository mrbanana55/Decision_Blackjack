"""Integration and contract tests for simulation endpoints and lifecycle."""

import pytest
from starlette.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_simulation_success_mock_mode():
    """Verify that submitting a valid simulation configuration in mock_mode returns HTTP 201."""
    payload = {
        "max_rounds": 5,
        "num_simulations": 1,
        "execution_mode": "visualized",
        "delay_ms": 100.0,
        "seed": 42,
        "entities": ["optimal", "jev", "laya"],
        "mock_mode": True,
        "table_rules": {
            "soft_17_rule": "S17",
            "blackjack_payout": 1.5,
            "hole_card_rule": "AMERICAN_PEEK",
            "insurance_allowed": True,
            "surrender_rule": "LATE",
            "double_after_split": True,
            "max_split_hands": 4,
            "resplit_aces": False,
            "num_decks": 6,
            "penetration": 0.75,
            "initial_bankroll": 1000.0,
            "min_bet": 10.0,
            "max_bet": 500.0,
        },
    }
    response = client.post("/api/simulations", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert "session_id" in data
    assert "run_id" in data
    assert data["max_rounds"] == 5
    assert data["entities"] == ["optimal", "jev", "laya"]
    assert data["websocket_url"].startswith("/ws/simulations/")
    assert data["table_rules"]["soft_17_rule"] == "S17"
    assert data["table_rules"]["min_bet"] == 10.0


def test_create_simulation_invalid_rules():
    """Verify that rule boundary violations return HTTP 422 without creating session state."""
    # min_bet exceeds max_bet
    payload = {
        "max_rounds": 10,
        "mock_mode": True,
        "table_rules": {
            "min_bet": 500.0,
            "max_bet": 100.0,
        },
    }
    response = client.post("/api/simulations", json=payload)
    assert response.status_code == 422
    assert "min_bet" in response.text


def test_create_simulation_invalid_entity():
    """Verify that unknown entity types are rejected with HTTP 422."""
    payload = {
        "max_rounds": 10,
        "entities": ["optimal", "invalid_player"],
        "mock_mode": True,
    }
    response = client.post("/api/simulations", json=payload)
    assert response.status_code == 422
    assert "Invalid entity" in response.text


def test_get_simulation_details():
    """Verify retrieving simulation status and configuration for an initialized session."""
    payload = {
        "max_rounds": 3,
        "seed": 101,
        "entities": ["optimal"],
        "mock_mode": True,
    }
    create_res = client.post("/api/simulations", json=payload)
    assert create_res.status_code == 201
    session_id = create_res.json()["session_id"]

    get_res = client.get(f"/api/simulations/{session_id}")
    assert get_res.status_code == 200
    details = get_res.json()
    assert details["session_id"] == session_id
    assert details["max_rounds"] == 3
    assert details["entities"] == ["optimal"]


def test_get_simulation_not_found():
    """Verify 404 response for unknown session identifier."""
    response = client.get("/api/simulations/sim-nonexistent")
    assert response.status_code == 404


def test_get_simulation_deviations():
    """Verify retrieving real-time strategy deviations endpoint."""
    payload = {
        "max_rounds": 3,
        "seed": 42,
        "entities": ["optimal", "jev"],
        "mock_mode": True,
    }
    create_res = client.post("/api/simulations", json=payload)
    assert create_res.status_code == 201
    session_id = create_res.json()["session_id"]

    dev_res = client.get(f"/api/simulations/{session_id}/deviations")
    assert dev_res.status_code == 200
    data = dev_res.json()
    assert data["session_id"] == session_id
    assert "entities" in data
    assert "optimal" in data["entities"]
    assert "jev" in data["entities"]
    assert "categories" in data["entities"]["jev"]


def test_control_simulation_via_rest():
    """Verify REST flow control commands (pause, resume, speed, stop)."""
    payload = {
        "max_rounds": 10,
        "delay_ms": 500.0,
        "entities": ["optimal"],
        "mock_mode": True,
    }
    create_res = client.post("/api/simulations", json=payload)
    session_id = create_res.json()["session_id"]

    # Start simulation
    start_res = client.post(f"/api/simulations/{session_id}/start")
    assert start_res.status_code == 200

    # Pause
    pause_res = client.post(
        f"/api/simulations/{session_id}/control",
        json={"command": "pause"},
    )
    assert pause_res.status_code == 200
    assert pause_res.json()["command_applied"] == "pause"

    # Set speed
    speed_res = client.post(
        f"/api/simulations/{session_id}/control",
        json={"command": "set_speed", "delay_ms": 100.0},
    )
    assert speed_res.status_code == 200
    assert speed_res.json()["command_applied"] == "set_speed"

    # Resume
    resume_res = client.post(
        f"/api/simulations/{session_id}/control",
        json={"command": "resume"},
    )
    assert resume_res.status_code == 200
    assert resume_res.json()["command_applied"] == "resume"

    # Stop
    stop_res = client.post(
        f"/api/simulations/{session_id}/control",
        json={"command": "stop"},
    )
    assert stop_res.status_code == 200
    assert stop_res.json()["command_applied"] == "stop"


def test_fault_recovery_and_retry():
    """Verify RNF-02 fault recovery: simulation enters PAUSED_ERROR and can be retried."""
    from app.api.manager import simulation_manager
    from app.simulation.types import SessionStatus

    payload = {
        "max_rounds": 5,
        "delay_ms": 100.0,
        "entities": ["optimal"],
        "mock_mode": True,
    }
    create_res = client.post("/api/simulations", json=payload)
    session_id = create_res.json()["session_id"]
    record = simulation_manager.get_session(session_id)
    assert record is not None

    # Simulate fault condition
    record.orchestrator._status = SessionStatus.PAUSED_ERROR
    record.orchestrator.failed_entity_id = "optimal"

    # Verify status reflects PAUSED_ERROR
    get_res = client.get(f"/api/simulations/{session_id}")
    assert get_res.json()["status"] == "PAUSED_ERROR"

    # Trigger retry via REST
    retry_res = client.post(
        f"/api/simulations/{session_id}/control",
        json={"command": "retry", "entity_id": "optimal"},
    )
    assert retry_res.status_code == 200
    assert retry_res.json()["command_applied"] == "retry"


def test_list_simulations_empty():
    """Verify GET /api/simulations returns empty list when no runs exist."""
    from app.api.manager import simulation_manager
    from app.persistence.database import get_db
    from unittest.mock import AsyncMock, MagicMock

    # Clear active sessions temporarily
    saved = simulation_manager._sessions
    simulation_manager._sessions = {}

    mock_session = AsyncMock()
    mock_res_count = MagicMock()
    mock_res_count.scalar.return_value = 0
    mock_res_items = MagicMock()
    mock_res_items.scalars.return_value.all.return_value = []
    mock_session.execute.side_effect = [mock_res_count, mock_res_items]

    async def mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_db
    try:
        response = client.get("/api/simulations")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20
    finally:
        app.dependency_overrides.pop(get_db, None)
        simulation_manager._sessions = saved


def test_list_simulations_with_records():
    """Verify GET /api/simulations returns paginated simulation items."""
    from app.api.manager import simulation_manager
    from app.persistence.database import get_db
    import uuid
    from datetime import datetime, UTC
    from decimal import Decimal
    from unittest.mock import AsyncMock, MagicMock
    from app.persistence.models import (
        Run,
        RunStatus,
        RunConfiguration,
        Soft17Rule,
        SplitAcesBlackjackRule,
        HoleCardRule,
        SurrenderRule,
        CharlieRule,
        Simulation,
        PlayerSession,
        PlayerType,
        SessionStatus,
    )

    test_run_id = uuid.uuid4()
    now = datetime.now(UTC)
    mock_run = MagicMock()
    mock_run.id = test_run_id
    mock_run.status = RunStatus.COMPLETED
    mock_run.started_at = now
    mock_run.finished_at = now
    mock_run.created_at = now

    mock_cfg = MagicMock()
    mock_cfg.rounds_per_simulation = 10
    mock_cfg.simulations_count = 1
    mock_cfg.user_seed = 42
    mock_run.configuration = mock_cfg

    mock_sim = MagicMock()
    mock_ps = MagicMock()
    mock_ps.player_type.value = "optimal"
    mock_ps.initial_bankroll = Decimal("1000.00")
    mock_ps.current_bankroll = Decimal("1050.00")
    mock_sim.player_sessions = [mock_ps]
    mock_sim.rounds = [MagicMock() for _ in range(10)]
    mock_run.simulations = [mock_sim]

    mock_session = AsyncMock()
    mock_res_count = MagicMock()
    mock_res_count.scalar.return_value = 1
    mock_res_items = MagicMock()
    mock_res_items.scalars.return_value.all.return_value = [mock_run]
    mock_session.execute.side_effect = [mock_res_count, mock_res_items]

    async def mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_db
    try:
        response = client.get("/api/simulations?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "run_id" in item
        assert "session_id" in item
        assert "status" in item
        assert "metrics" in item
        assert data["page"] == 1
        assert data["page_size"] == 10
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_get_historical_simulation_from_db():
    """Verify GET /api/simulations/{id} falls back to DB when not in active memory."""
    from app.persistence.database import get_db
    import uuid
    from datetime import datetime, UTC
    from decimal import Decimal
    from unittest.mock import AsyncMock, MagicMock
    from app.persistence.models import (
        Run,
        RunStatus,
        Soft17Rule,
        SplitAcesBlackjackRule,
        HoleCardRule,
        SurrenderRule,
        CharlieRule,
    )

    test_run_id = uuid.uuid4()
    now = datetime.now(UTC)
    mock_run = MagicMock()
    mock_run.id = test_run_id
    mock_run.status = RunStatus.COMPLETED
    mock_run.started_at = now
    mock_run.finished_at = now
    mock_run.created_at = now

    mock_cfg = MagicMock()
    mock_cfg.rounds_per_simulation = 10
    mock_cfg.simulations_count = 1
    mock_cfg.user_seed = 42
    mock_cfg.soft_17_rule.name = "STAND"
    mock_cfg.blackjack_payout_ratio = Decimal("1.500")
    mock_cfg.hole_card_rule.name = "AMERICAN_PEEK"
    mock_cfg.insurance_enabled = True
    mock_cfg.surrender_rule.name = "LATE"
    mock_cfg.das_enabled = True
    mock_cfg.max_resplit = 3
    mock_cfg.rsa_enabled = False
    mock_cfg.hit_split_aces = False
    mock_cfg.number_of_decks = 6
    mock_cfg.penetration = Decimal("0.750")
    mock_cfg.burn_cards = 0
    mock_cfg.initial_bankroll = Decimal("1000.00")
    mock_cfg.minimum_bet = Decimal("10.00")
    mock_cfg.maximum_bet = Decimal("500.00")
    mock_run.configuration = mock_cfg

    mock_sim = MagicMock()
    mock_ps = MagicMock()
    mock_ps.player_type.value = "optimal"
    mock_ps.initial_bankroll = Decimal("1000.00")
    mock_ps.current_bankroll = Decimal("1050.00")
    mock_sim.player_sessions = [mock_ps]
    mock_sim.rounds = [MagicMock() for _ in range(10)]
    mock_run.simulations = [mock_sim]

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_run
    mock_session.execute.return_value = mock_res

    async def mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_db
    try:
        response = client.get(f"/api/simulations/{test_run_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == str(test_run_id)
        assert data["status"] == "COMPLETED"
        assert "optimal" in data["entities"]
        assert "table_rules" in data
        assert data["table_rules"]["soft_17_rule"] == "S17"
    finally:
        app.dependency_overrides.pop(get_db, None)

