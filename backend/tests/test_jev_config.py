"""Unit tests for JevConfig and environment settings."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.integrations.jev.config import JevConfig


def test_jev_config_defaults():
    """Verify default JevConfig values when no environment override exists."""
    with patch.dict(os.environ, {}, clear=True):
        config = JevConfig()
        assert config.api_url == "https://api.typesafe.ai/v1/systemone"
        assert config.model == "jev-latest"
        assert config.timeout_seconds == 15.0
        assert config.connect_timeout_seconds == 3.0
        assert config.max_retries == 3
        assert config.api_key == ""


def test_jev_config_env_override():
    """Verify TYPESAFE_* environment variables override configuration defaults."""
    env = {
        "TYPESAFE_API_KEY": "test_secret_key_123",
        "TYPESAFE_API_URL": "https://custom.typesafe.ai/v1/systemone",
        "TYPESAFE_MODEL": "jev-custom-model",
        "TYPESAFE_TIMEOUT_SECONDS": "25.0",
        "TYPESAFE_CONNECT_TIMEOUT_SECONDS": "5.0",
        "TYPESAFE_MAX_RETRIES": "5",
    }
    with patch.dict(os.environ, env):
        config = JevConfig()
        assert config.api_key == "test_secret_key_123"
        assert config.api_url == "https://custom.typesafe.ai/v1/systemone"
        assert config.model == "jev-custom-model"
        assert config.timeout_seconds == 25.0
        assert config.connect_timeout_seconds == 5.0
        assert config.max_retries == 5


def test_jev_config_url_helpers():
    """Verify get_effective_url and get_base_url URL helper methods."""
    config = JevConfig(api_url="https://api.typesafe.ai/v1/systemone/")
    assert config.get_effective_url() == "https://api.typesafe.ai/v1/systemone"
    assert config.get_base_url() == "https://api.typesafe.ai"

    # Custom port and path
    config2 = JevConfig(api_url="http://localhost:8000/v1/systemone")
    assert config2.get_base_url() == "http://localhost:8000"


def test_jev_config_validation():
    """Verify validation boundaries on timeout and retry settings."""
    with pytest.raises(ValidationError):
        JevConfig(timeout_seconds=0.01)  # ge=0.1

    with pytest.raises(ValidationError):
        JevConfig(max_retries=15)  # le=10
