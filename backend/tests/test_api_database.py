"""Integration and contract tests for database maintenance and storage purge."""

from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from starlette.testclient import TestClient

from app.api.manager import simulation_manager
from app.api.schemas import SimulationConfigRequest
from app.main import app
from app.persistence.database import get_db
from app.simulation.types import SessionStatus

client = TestClient(app)


def test_purge_database_conflict_when_simulation_active():
    """Verify DELETE /api/database returns HTTP 409 Conflict when a simulation is running."""
    session_id = f"sim-{uuid.uuid4().hex[:6]}"
    mock_orch = MagicMock()
    mock_orch.status = SessionStatus.RUNNING
    mock_orch.event_bus = MagicMock()

    config = SimulationConfigRequest(mock_mode=True)
    simulation_manager.register_session(
        session_id=session_id,
        run_id=str(uuid.uuid4()),
        config=config,
        orchestrator=mock_orch,
    )

    try:
        response = client.delete("/api/database")
        assert response.status_code == 409
        assert "cannot purge database" in response.json()["detail"].lower()
    finally:
        simulation_manager._sessions.pop(session_id, None)


def test_purge_database_conflict_when_simulation_paused():
    """Verify POST /api/database/clear returns HTTP 409 Conflict when a simulation is paused."""
    session_id = f"sim-{uuid.uuid4().hex[:6]}"
    mock_orch = MagicMock()
    mock_orch.status = SessionStatus.PAUSED
    mock_orch.event_bus = MagicMock()

    config = SimulationConfigRequest(mock_mode=True)
    simulation_manager.register_session(
        session_id=session_id,
        run_id=str(uuid.uuid4()),
        config=config,
        orchestrator=mock_orch,
    )

    try:
        response = client.post("/api/database/clear")
        assert response.status_code == 409
        assert "cannot purge database" in response.json()["detail"].lower()
    finally:
        simulation_manager._sessions.pop(session_id, None)


def test_purge_database_success_delete():
    """Verify DELETE /api/database returns HTTP 200 and purges all 15 tables when idle."""
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
        assert "runs" in data["cleared_tables"]
        assert "decisions" in data["cleared_tables"]
        assert "timestamp" in data
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_purge_database_success_post_clear():
    """Verify POST /api/database/clear returns HTTP 200 and purges all 15 tables when idle."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    async def mock_db():
        yield mock_session

    app.dependency_overrides[get_db] = mock_db
    try:
        response = client.post("/api/database/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cleared"
        assert data["tables_purged"] == 15
        assert len(data["cleared_tables"]) == 15
    finally:
        app.dependency_overrides.pop(get_db, None)
