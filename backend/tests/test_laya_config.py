"""Unit tests for LayaConfig and Docker host-bridge URL normalization."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.integrations.laya.config import LayaConfig, is_running_in_docker


def test_laya_config_defaults():
    """Verify default LayaConfig values when no environment override exists."""
    with patch.dict(os.environ, {}, clear=True):
        config = LayaConfig()
        assert config.base_url == "http://127.0.0.1:1234"
        assert config.timeout_seconds == 15.0
        assert config.connect_timeout_seconds == 1.5
        assert config.max_retries == 2


def test_laya_config_env_override():
    """Verify LAYA_BASE_URL from environment overrides default base_url."""
    with patch.dict(os.environ, {"LAYA_BASE_URL": "http://127.0.0.1:8000"}):
        config = LayaConfig()
        assert config.base_url == "http://127.0.0.1:8000"


def test_laya_config_custom_port():
    """Verify arbitrary custom host port configuration."""
    config = LayaConfig(base_url="http://127.0.0.1:9999")
    assert config.base_url == "http://127.0.0.1:9999"


def test_laya_config_normalization_in_docker():
    """Verify that localhost/127.0.0.1/0.0.0.0 get normalized to host.docker.internal inside Docker."""
    with patch("app.integrations.laya.config.is_running_in_docker", return_value=True):
        # 127.0.0.1 with port
        cfg1 = LayaConfig(base_url="http://127.0.0.1:1234")
        assert cfg1.get_effective_url() == "http://host.docker.internal:1234"

        # localhost with custom port
        cfg2 = LayaConfig(base_url="http://localhost:8000")
        assert cfg2.get_effective_url() == "http://host.docker.internal:8000"

        # 0.0.0.0 with port
        cfg3 = LayaConfig(base_url="http://0.0.0.0:1234")
        assert cfg3.get_effective_url() == "http://host.docker.internal:1234"

        # Remote hostname should NOT be changed
        cfg4 = LayaConfig(base_url="http://external-ai-host:1234")
        assert cfg4.get_effective_url() == "http://external-ai-host:1234"

        # Trailing slash should be stripped
        cfg5 = LayaConfig(base_url="http://127.0.0.1:1234/")
        assert cfg5.get_effective_url() == "http://host.docker.internal:1234"


def test_laya_config_no_normalization_outside_docker():
    """Verify that URLs are preserved without change outside Docker."""
    with patch("app.integrations.laya.config.is_running_in_docker", return_value=False):
        cfg = LayaConfig(base_url="http://127.0.0.1:1234")
        assert cfg.get_effective_url() == "http://127.0.0.1:1234"

        cfg2 = LayaConfig(base_url="http://localhost:5000/")
        assert cfg2.get_effective_url() == "http://localhost:5000"


def test_laya_config_validation():
    """Verify validation boundaries on timeout and retry settings."""
    with pytest.raises(ValidationError):
        LayaConfig(timeout_seconds=0.01)  # ge=0.1

    with pytest.raises(ValidationError):
        LayaConfig(max_retries=10)  # le=5


def test_is_running_in_docker_detection():
    """Verify detection logic via .dockerenv and IN_DOCKER env var."""
    with patch("os.path.exists", side_effect=lambda p: p == "/.dockerenv"):
        assert is_running_in_docker() is True

    with patch("os.path.exists", return_value=False):
        with patch.dict(os.environ, {"IN_DOCKER": "true"}):
            assert is_running_in_docker() is True
        with patch.dict(os.environ, {"IN_DOCKER": "0"}):
            assert is_running_in_docker() is False
