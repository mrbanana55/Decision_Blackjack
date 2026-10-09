"""FastAPI application entry point for Decision_Blackjack."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router

app = FastAPI(
    title="Decision_Blackjack API",
    description="Multi-model simulation engine and telemetry API for Blackjack decision analysis",
    version="0.1.0",
)

# Configure CORS to permit requests from the frontend client
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root metadata endpoint."""
    return {
        "name": "Decision_Blackjack API",
        "status": "running",
        "version": "0.1.0",
    }
