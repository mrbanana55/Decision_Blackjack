"""Centralized environment variable loader for Decision_Blackjack."""

import os
from pathlib import Path
from dotenv import find_dotenv, load_dotenv


def load_env_file() -> str | None:
    """Locate and load .env file into os.environ if variables are not already set.

    Resolution order:
    1. /app/.env (standard container path when root .env is bind-mounted)
    2. Traversing parent directories from this file up to the project root
    3. find_dotenv(usecwd=True) searching upward from the current working directory
    """
    # 1. Docker container bind-mount location
    container_env = Path("/app/.env")
    if container_env.is_file():
        load_dotenv(container_env, override=False)
        return str(container_env)

    # 2. Walk parent directories from this file (backend/app/env.py -> backend -> root)
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return str(candidate)

    # 3. Fallback to searching upward from current working directory
    cwd_env = find_dotenv(usecwd=True)
    if cwd_env and Path(cwd_env).is_file():
        load_dotenv(cwd_env, override=False)
        return cwd_env

    return None
