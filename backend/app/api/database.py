"""Database maintenance and purge endpoints."""

from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.manager import simulation_manager
from app.api.schemas import PurgeDatabaseResponse
from app.persistence.database import get_db
from app.persistence.repositories import RunRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/database", tags=["Maintenance"])


async def _execute_database_purge(db: AsyncSession) -> PurgeDatabaseResponse:
    """Validate safety guard and execute atomic database purge across all 15 tables."""
    if simulation_manager.has_active_simulations():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot purge database while simulations are actively running or paused. Stop active simulations first.",
        )

    repo = RunRepository(db)
    cleared_tables = await repo.purge_all_tables()

    # Clear inactive/completed in-memory session records
    simulation_manager._sessions.clear()

    return PurgeDatabaseResponse(
        status="cleared",
        tables_purged=len(cleared_tables),
        cleared_tables=cleared_tables,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.delete(
    "",
    response_model=PurgeDatabaseResponse,
    summary="Purge all records across all database tables (Reset Database)",
)
async def purge_database(
    db: AsyncSession = Depends(get_db),
) -> PurgeDatabaseResponse:
    """Purge all records across all 15 relational tables."""
    return await _execute_database_purge(db)


@router.post(
    "/clear",
    response_model=PurgeDatabaseResponse,
    summary="Purge all records across all database tables (Reset Database alias)",
)
async def clear_database(
    db: AsyncSession = Depends(get_db),
) -> PurgeDatabaseResponse:
    """Purge all records across all 15 relational tables (POST alias)."""
    return await _execute_database_purge(db)
