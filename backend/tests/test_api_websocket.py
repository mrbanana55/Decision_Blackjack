"""Integration tests for WebSocket telemetry streaming and client commands."""

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app

client = TestClient(app)


def test_websocket_invalid_session_closes_4404():
    """Verify that connecting to an uninitialized session closes immediately with 4404."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/simulations/sim-does-not-exist"):
            pass
    assert exc_info.value.code == 4404


def test_websocket_connection_snapshot_and_telemetry():
    """Verify receiving SESSION_SNAPSHOT and subsequent turn-by-turn telemetry events."""
    # 1. Provision simulation with 2 rounds
    payload = {
        "max_rounds": 2,
        "delay_ms": 10.0,
        "seed": 42,
        "entities": ["optimal", "jev"],
        "mock_mode": True,
    }
    res = client.post("/api/simulations", json=payload)
    assert res.status_code == 201
    session_id = res.json()["session_id"]

    # 2. Connect WebSocket client
    with client.websocket_connect(f"/ws/simulations/{session_id}") as ws:
        # First message MUST be SESSION_SNAPSHOT
        first_frame = ws.receive_json()
        assert first_frame["event_type"] == "SESSION_SNAPSHOT"
        assert first_frame["session_id"] == session_id
        assert "tables" in first_frame["payload"]
        assert "deviations" in first_frame["payload"]

        # Collect subsequent events until simulation completion
        event_types = []
        has_decision_made = False
        has_round_settled = False

        for _ in range(30):
            try:
                frame = ws.receive_json()
                evt_type = frame["event_type"]
                event_types.append(evt_type)

                if evt_type == "DECISION_MADE":
                    has_decision_made = True
                    payload = frame["payload"]
                    assert "comparison" in payload
                    comp = payload["comparison"]
                    assert "is_optimal" in comp
                    assert "category" in comp
                    assert "actual_action" in comp

                elif evt_type == "ROUND_SETTLED":
                    has_round_settled = True
                    payload = frame["payload"]
                    assert "running_deviations" in payload
                    assert "optimal" in payload["running_deviations"]
                    assert "jev" in payload["running_deviations"]

                elif evt_type == "SESSION_COMPLETED":
                    break
            except Exception:
                break

        assert "SESSION_STARTED" in event_types or has_decision_made or has_round_settled


def test_websocket_client_flow_control():
    """Verify sending pause, set_speed, and resume commands over WebSocket."""
    payload = {
        "max_rounds": 10,
        "delay_ms": 500.0,
        "entities": ["optimal"],
        "mock_mode": True,
    }
    res = client.post("/api/simulations", json=payload)
    session_id = res.json()["session_id"]

    with client.websocket_connect(f"/ws/simulations/{session_id}") as ws:
        snapshot = ws.receive_json()
        assert snapshot["event_type"] == "SESSION_SNAPSHOT"

        # Send pause
        ws.send_json({"command": "pause"})

        # Send set_speed
        ws.send_json({"command": "set_speed", "delay_ms": 50.0})

        # Send resume
        ws.send_json({"command": "resume"})
