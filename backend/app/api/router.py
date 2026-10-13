"""Consolidated API router mounting all sub-routers for Decision_Blackjack."""

from fastapi import APIRouter

from app.api.database import router as database_router
from app.api.export import router as export_router
from app.api.health import router as health_router
from app.api.simulations import router as simulations_router
from app.api.websocket import router as websocket_router

api_router = APIRouter()

# Register sub-routers
api_router.include_router(health_router)
api_router.include_router(simulations_router)
api_router.include_router(websocket_router)
api_router.include_router(export_router)
api_router.include_router(database_router)

__all__ = ["api_router"]
