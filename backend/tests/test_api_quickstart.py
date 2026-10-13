"""End-to-end quickstart validation covering all 6 scenarios in quickstart.md."""

from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from starlette.testclient import TestClient

from app.api.manager import simulation_manager
from app.main import app
from app.persistence.database import get_db

client = TestClient(app)


def test_quickstart_scenario_1_provisioning():
    """Scenario 1: Provision Multi-Agent Simulation with Custom Casino Rules."""
    payload = {
        "max_rounds": 10,
        "num_simulations": 1,
        "execution_mode": "visualized",
        "delay_ms": 200.0,
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
            "hit_split_aces": False,
            "num_decks": 6,
            "penetration": 0.75,
            "burn_cards_count": 0,
            "initial_bankroll": 1000.0,
            "min_bet": 10.0,
            "max_bet": 500.0,
            "stop_on_all_bankrupt": True,
        },
    }
    response = client.post("/api/simulations", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert "run_id" in data
    assert data["status"] == "INITIALIZING"
    assert data["websocket_url"] == f"/ws/simulations/{data['session_id']}"
    assert data["table_rules"]["soft_17_rule"] == "S17"
    assert data["table_rules"]["blackjack_payout"] == 1.5


def test_quickstart_scenario_2_streaming_and_deviations():
    """Scenario 2: Stream Live Telemetry and Basic Strategy Deviations over WebSocket."""
    payload = {
        "max_rounds": 3,
        "execution_mode": "visualized",
        "delay_ms": 10.0,
        "seed": 1234,
        "entities": ["optimal", "jev"],
        "mock_mode": True,
    }
    create_res = client.post("/api/simulations", json=payload)
    session_id = create_res.json()["session_id"]

    events_received = []
    with client.websocket_connect(f"/ws/simulations/{session_id}") as ws:
        # Snapshot is received immediately
        snap = ws.receive_json()
        assert snap["event_type"] == "SESSION_SNAPSHOT"

        while True:
            frame = ws.receive_json()
            events_received.append(frame["event_type"])
            if frame["event_type"] == "DECISION_MADE":
                payload = frame["payload"]
                assert "comparison" in payload
                assert "is_optimal" in payload["comparison"]
                assert "optimal_action" in payload["comparison"]
                assert "category" in payload["comparison"]
            elif frame["event_type"] == "ROUND_SETTLED":
                assert "running_deviations" in frame["payload"]
            elif frame["event_type"] == "SESSION_COMPLETED":
                break

    assert "ROUND_STARTED" in events_received
    assert "DECISION_MADE" in events_received
    assert "ROUND_SETTLED" in events_received

    # Query deviation analytics via REST
    dev_res = client.get(f"/api/simulations/{session_id}/deviations")
    assert dev_res.status_code == 200
    dev_data = dev_res.json()
    assert dev_data["session_id"] == session_id
    assert "optimal" in dev_data["entities"]
    assert "jev" in dev_data["entities"]


def test_quickstart_scenario_3_flow_control():
    """Scenario 3: Interactive Flow Control & Dynamic Speed Adjustment."""
    payload = {
        "max_rounds": 5,
        "delay_ms": 200.0,
        "entities": ["optimal"],
        "mock_mode": True,
    }
    create_res = client.post("/api/simulations", json=payload)
    session_id = create_res.json()["session_id"]

    # Start simulation
    client.post(f"/api/simulations/{session_id}/start")

    # Pause
    pause_res = client.post(f"/api/simulations/{session_id}/control", json={"command": "pause"})
    assert pause_res.status_code == 200
    assert pause_res.json()["command_applied"] == "pause"

    # Set speed
    speed_res = client.post(
        f"/api/simulations/{session_id}/control",
        json={"command": "set_speed", "delay_ms": 50.0},
    )
    assert speed_res.status_code == 200
    assert speed_res.json()["command_applied"] == "set_speed"

    # Resume
    resume_res = client.post(f"/api/simulations/{session_id}/control", json={"command": "resume"})
    assert resume_res.status_code == 200
    assert resume_res.json()["command_applied"] == "resume"

    # Stop
    stop_res = client.post(f"/api/simulations/{session_id}/control", json={"command": "stop"})
    assert stop_res.status_code == 200
    assert stop_res.json()["command_applied"] == "stop"


def test_quickstart_scenario_4_single_export():
    """Scenario 4: Export Single Simulation JSON Artifact."""
    test_run_id = uuid.uuid4()
    mock_run_data = {
        "run": {
            "id": str(test_run_id),
            "status": "COMPLETED",
            "configuration": {"soft_17_rule": "S17"},
            "simulations": [],
        }
    }

    mock_session = AsyncMock()
    async def mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_db
    try:
        from unittest.mock import patch
        with patch("app.api.export.RunExporter") as MockExporter:
            exporter_instance = MockExporter.return_value
            exporter_instance.get_run_export_dict = AsyncMock(return_value=mock_run_data)

            response = client.get(f"/api/export/simulations/{test_run_id}")
            assert response.status_code == 200
            assert f'attachment; filename="simulation_{test_run_id}_export.json"' in response.headers["content-disposition"]
            assert response.json()["run"]["id"] == str(test_run_id)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_quickstart_scenario_5_database_export():
    """Scenario 5: Export Full Database JSON Archive."""
    async def mock_stream():
        yield '{\n  "archive_metadata": {"total_runs": 2},\n  "runs": []\n}\n'

    mock_session = AsyncMock()
    async def mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_db
    try:
        from unittest.mock import patch
        with patch("app.api.export.RunExporter") as MockExporter:
            exporter_instance = MockExporter.return_value
            exporter_instance.export_all_runs_streaming.return_value = mock_stream()

            response = client.get("/api/export/database")
            assert response.status_code == 200
            assert "decision_blackjack_full_export_" in response.headers["content-disposition"]
            assert response.json()["archive_metadata"]["total_runs"] == 2
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_quickstart_scenario_6_reset_database():
    """Scenario 6: Reset / Clear Database across all 15 tables."""
    # Ensure no active simulation is running
    simulation_manager._sessions.clear()

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    async def mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_db
    try:
        response = client.delete("/api/database")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
        assert data["tables_purged"] == 15
        assert len(data["cleared_tables"]) == 15

        # Query catalog after purge
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_items = MagicMock()
        mock_items.scalars.return_value.all.return_value = []
        mock_session.execute.side_effect = [mock_count, mock_items]

        cat_res = client.get("/api/simulations")
        assert cat_res.status_code == 200
        assert cat_res.json()["items"] == []
        assert cat_res.json()["total"] == 0
    finally:
        app.dependency_overrides.pop(get_db, None)
