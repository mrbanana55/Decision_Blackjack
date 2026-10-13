"""Integration and contract tests for JSON export endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from starlette.testclient import TestClient

from app.api.manager import simulation_manager
from app.api.schemas import SimulationConfigRequest
from app.main import app
from app.persistence.database import get_db

client = TestClient(app)


def test_export_single_simulation_not_found():
    """Verify exporting a non-existent simulation returns HTTP 404."""
    random_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res

    async def mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_db
    try:
        response = client.get(f"/api/export/simulations/{random_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_export_single_simulation_invalid_id():
    """Verify exporting an invalid identifier returns HTTP 404."""
    response = client.get("/api/export/simulations/invalid-identifier-123")
    assert response.status_code == 404


def test_export_single_simulation_success():
    """Verify exporting an existing run returns HTTP 200, attachment header, and valid payload."""
    test_run_id = uuid.uuid4()
    mock_run_data = {
        "run": {
            "id": str(test_run_id),
            "status": "COMPLETED",
            "created_at": datetime.now(UTC).isoformat(),
            "configuration": {
                "soft_17_rule": "S17",
                "blackjack_payout_ratio": 1.5,
            },
            "simulations": [],
        }
    }

    async def mock_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db
    try:
        with patch("app.api.export.RunExporter") as MockExporter:
            exporter_instance = MockExporter.return_value
            exporter_instance.get_run_export_dict = AsyncMock(return_value=mock_run_data)

            response = client.get(f"/api/export/simulations/{test_run_id}")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            assert (
                f'attachment; filename="simulation_{test_run_id}_export.json"'
                in response.headers["content-disposition"]
            )
            data = response.json()
            assert "run" in data
            assert data["run"]["id"] == str(test_run_id)
            exporter_instance.get_run_export_dict.assert_awaited_once_with(test_run_id)
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_export_single_simulation_via_active_session_id():
    """Verify exporting by session_id resolves the session's run_id and exports correctly."""
    session_id = f"sim-test-{uuid.uuid4().hex[:6]}"
    target_run_id = uuid.uuid4()

    # Register mock session in manager
    mock_orchestrator = MagicMock()
    mock_orchestrator.event_bus = MagicMock()
    mock_orchestrator.event_bus.subscribe = MagicMock()
    config = SimulationConfigRequest(mock_mode=True)
    simulation_manager.register_session(
        session_id=session_id,
        run_id=str(target_run_id),
        config=config,
        orchestrator=mock_orchestrator,
    )

    mock_run_data = {
        "run": {
            "id": str(target_run_id),
            "status": "RUNNING",
            "simulations": [],
        }
    }

    async def mock_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db
    try:
        with patch("app.api.export.RunExporter") as MockExporter:
            exporter_instance = MockExporter.return_value
            exporter_instance.get_run_export_dict = AsyncMock(return_value=mock_run_data)

            response = client.get(f"/api/export/simulations/{session_id}")
            assert response.status_code == 200
            assert (
                f'attachment; filename="simulation_{target_run_id}_export.json"'
                in response.headers["content-disposition"]
            )
            data = response.json()
            assert data["run"]["id"] == str(target_run_id)
            exporter_instance.get_run_export_dict.assert_awaited_once_with(target_run_id)
    finally:
        app.dependency_overrides.pop(get_db, None)
        simulation_manager._sessions.pop(session_id, None)


def test_export_full_database_streaming():
    """Verify GET /api/export/database returns streamed full archive with Content-Disposition header."""
    async def mock_generator():
        yield '{\n  "archive_metadata": {\n'
        yield '    "total_runs": 1\n'
        yield '  },\n  "runs": [\n'
        yield '    {"id": "test-run"}\n'
        yield "  ]\n}\n"

    async def mock_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db
    try:
        with patch("app.api.export.RunExporter") as MockExporter:
            exporter_instance = MockExporter.return_value
            exporter_instance.export_all_runs_streaming.return_value = mock_generator()

            response = client.get("/api/export/database")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("application/json")
            assert "decision_blackjack_full_export_" in response.headers["content-disposition"]
            assert response.headers["content-disposition"].endswith('.json"')

            data = response.json()
            assert "archive_metadata" in data
            assert data["archive_metadata"]["total_runs"] == 1
            assert len(data["runs"]) == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
