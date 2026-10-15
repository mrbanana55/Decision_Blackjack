"""FastAPI application entry point for Decision_Blackjack."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router
from app.env import load_env_file

load_env_file()

tags_metadata = [
    {
        "name": "Simulations",
        "description": "Simulation provisioning, lifecycle, configuration, historical catalog, and interactive flow control.",
    },
    {
        "name": "Analytics",
        "description": "Real-time decision telemetry and Basic Strategy deviation analytics.",
    },
    {
        "name": "Export",
        "description": "Granular single-simulation and full-database hierarchical JSON data exports.",
    },
    {
        "name": "Maintenance",
        "description": "Database reset, atomic table truncation, and storage clearing operations.",
    },
    {
        "name": "Health",
        "description": "Health probes and external AI provider connectivity status.",
    },
]

app = FastAPI(
    title="Decision_Blackjack API",
    description="Multi-model simulation engine and real-time telemetry API for Blackjack decision analysis comparing Jev, Laya, and Basic Strategy.",
    version="0.1.0",
    openapi_tags=tags_metadata,
)

# Configure CORS to permit requests from the frontend client
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://frontend:5173",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register consolidated API router
app.include_router(api_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root metadata endpoint."""
    return {
        "name": "Decision_Blackjack API",
        "status": "running",
        "version": "0.1.0",
    }
