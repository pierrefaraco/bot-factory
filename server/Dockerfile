FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    FASTEMBED_CACHE_PATH=/home/appuser/.cache/fastembed

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy dependency manifests first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies only (project source isn't copied yet)
RUN uv sync --frozen --no-dev --no-install-project

# Copy application code
COPY src ./src
COPY db ./db
COPY config ./config

# Install the project itself now that its source is present
RUN uv sync --frozen --no-dev

# Create non-root user for security
# The embedding model cache dir is created here, owned by appuser, so the
# fastembed_cache volume (docker-compose.yml) mounted on it inherits that
# ownership on first use instead of being root-owned and unwritable.
RUN useradd -m -u 1000 appuser && \
    mkdir -p "$FASTEMBED_CACHE_PATH" && \
    chown -R appuser:appuser /app /home/appuser/.cache
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:444/api/health || exit 1

# Expose port
EXPOSE 444

# Run the ASGI application
CMD ["uvicorn", "src.asgi:app", "--host", "0.0.0.0", "--port", "444"]
