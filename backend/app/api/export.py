"""Export endpoints for single-run and full-database JSON downloads."""

from datetime import datetime, timezone
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.manager import simulation_manager
from app.persistence.database import get_db
from app.persistence.exporter import EntityJSONEncoder, RunExporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get(
    "/simulations/{session_or_run_id}",
    summary="Export a single simulation run as a hierarchical JSON file",
)
async def export_simulation(
    session_or_run_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the complete hierarchical JSON document for a single simulation run."""
    # Check if session_or_run_id matches an active session in memory
    record = simulation_manager.get_session(session_or_run_id)
    target_id_str = record.run_id if record else session_or_run_id

    try:
        target_run_id = uuid.UUID(target_id_str)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{session_or_run_id}' not found.",
        ) from exc

    exporter = RunExporter(db)
    try:
        run_data = await exporter.get_run_export_dict(target_run_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{session_or_run_id}' not found.",
        ) from exc

    payload = json.dumps(run_data, cls=EntityJSONEncoder, indent=2)
    filename = f"simulation_{target_run_id}_export.json"

    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/database",
    summary="Export entire database archive as a comprehensive JSON file",
)
async def export_database(
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Download all historical simulation runs and metrics as a chunked JSON archive."""
    exporter = RunExporter(db)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"decision_blackjack_full_export_{timestamp}.json"

    return StreamingResponse(
        exporter.export_all_runs_streaming(),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
