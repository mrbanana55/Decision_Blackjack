FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Optimize python and uv execution in container
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    IN_DOCKER=true

# Copy dependency definition
COPY pyproject.toml ./

# Install dependencies into .venv
RUN uv sync --no-install-project

# Copy remaining project source
COPY . .

# Put virtual environment on PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Start Uvicorn with hot-reload enabled
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]