import os
from typing import Any
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel, Field, field_validator

from app.env import load_env_file

load_env_file()


class JevConfig(BaseModel):
    """Runtime configuration for TypeSafe Jev remote API connectivity."""

    api_key: str = Field(
        default_factory=lambda: os.getenv("TYPESAFE_API_KEY", ""),
        description="TypeSafe API key specified in .env as TYPESAFE_API_KEY",
    )

    @field_validator("api_key", mode="before")
    @classmethod
    def _clean_api_key(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip().strip("'\"")
        return str(v) if v is not None else ""

    api_url: str = Field(
        default_factory=lambda: os.getenv(
            "TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone"
        ),
        description="TypeSafe System One endpoint URL",
    )
    model: str = Field(
        default_factory=lambda: os.getenv("TYPESAFE_MODEL", "jev-latest"),
        description="TypeSafe model identifier/alias (e.g. jev-latest)",
    )
    timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("TYPESAFE_TIMEOUT_SECONDS", "15.0")),
        ge=0.1,
        le=120.0,
        description="Maximum request timeout for inference calls",
    )
    connect_timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("TYPESAFE_CONNECT_TIMEOUT_SECONDS", "3.0")),
        ge=0.1,
        le=10.0,
        description="Maximum connection establishment timeout",
    )
    max_retries: int = Field(
        default_factory=lambda: int(os.getenv("TYPESAFE_MAX_RETRIES", "3")),
        ge=0,
        le=10,
        description="Transient and rate limit retry attempts before raising AgentFaultError",
    )

    def get_effective_url(self) -> str:
        """Return the effective endpoint URL with trailing slash stripped."""
        return self.api_url.rstrip("/")

    def get_base_url(self) -> str:
        """Extract the root host base URL (scheme + netloc) for health probes."""
        parsed = urlparse(self.get_effective_url())
        if not parsed.netloc:
            return self.get_effective_url()
        return urlunparse((parsed.scheme or "https", parsed.netloc, "", "", "", "")).rstrip("/")
