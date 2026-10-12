"""Configuration and connection options for the local Laya inference service."""

import os
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel, Field


def is_running_in_docker() -> bool:
    """Determine whether the current process is running inside a Docker container."""
    if os.path.exists("/.dockerenv"):
        return True
    if os.getenv("IN_DOCKER", "").lower() in ("1", "true", "yes"):
        return True
    # Container check: cgroup inspection fallback
    try:
        if os.path.exists("/proc/1/cgroup"):
            with open("/proc/1/cgroup", encoding="utf-8") as f:
                content = f.read()
                if "docker" in content or "containerd" in content:
                    return True
    except OSError:
        return False
    return False


class LayaConfig(BaseModel):
    """Runtime configuration for local Laya server connectivity."""

    base_url: str = Field(
        default_factory=lambda: os.getenv("LAYA_BASE_URL", "http://127.0.0.1:1234"),
        description="Target Laya base URL specified in .env as LAYA_BASE_URL",
    )
    timeout_seconds: float = Field(
        default_factory=lambda: float(os.getenv("LAYA_TIMEOUT_SECONDS", "15.0")),
        ge=0.1,
        le=120.0,
        description="Maximum request timeout for inference calls",
    )
    connect_timeout_seconds: float = Field(
        default=1.5,
        ge=0.1,
        le=10.0,
        description="Maximum connection establishment timeout",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Transient retry attempts before raising AgentFaultError",
    )

    def get_effective_url(self) -> str:
        """Resolve the effective URL, normalizing localhost/127.0.0.1 to host.docker.internal inside Docker."""
        raw_url = self.base_url.rstrip("/")
        if not is_running_in_docker():
            return raw_url

        parsed = urlparse(raw_url)
        if parsed.hostname in ("127.0.0.1", "localhost", "0.0.0.0"):
            port_part = f":{parsed.port}" if parsed.port else ""
            new_netloc = f"host.docker.internal{port_part}"
            return urlunparse((
                parsed.scheme or "http",
                new_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )).rstrip("/")

        return raw_url
