"""Health check endpoint router."""

from fastapi import APIRouter
import os

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return operational health status for container health probes."""
    return {
        "status": "ok",
        "service": "backend",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }
