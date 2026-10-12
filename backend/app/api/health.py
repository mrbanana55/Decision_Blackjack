"""Health check endpoint router."""

import os
from typing import Any
from fastapi import APIRouter

from app.integrations.laya import LayaClient

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return operational health status for container health probes."""
    return {
        "status": "ok",
        "service": "backend",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


@router.get("/health/laya")
async def laya_health_check() -> dict[str, Any]:
    """Probe Laya local inference server health status."""
    client = LayaClient()
    try:
        health = await client.check_health()
        return {
            "status": "ok",
            "laya": health.model_dump(),
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "error": str(exc),
        }
    finally:
        await client.close()
