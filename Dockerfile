# =============================================================================
# BASE STAGE - Common dependencies
# =============================================================================
FROM python:3.14-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# =============================================================================
# BUILDER STAGE - Build dependencies
# =============================================================================
FROM base AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv sync --frozen --no-dev

# =============================================================================
# BUILDER-DEV STAGE - Development dependencies
# =============================================================================
FROM builder AS builder-dev

# Install dev dependencies
RUN uv sync --frozen

# =============================================================================
# DEVELOPMENT STAGE
# =============================================================================
FROM base AS development

# Copy virtual environment from builder-dev
COPY --from=builder-dev /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install additional dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Default command for development
CMD ["uvicorn", "eld_logs.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# PRODUCTION STAGE
# =============================================================================
FROM base AS production

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup . .

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R appuser:appgroup /app

# Collect static files
RUN python manage.py collectstatic --noinput --clear

USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/schema/')" || exit 1

# Production command with gunicorn + uvicorn workers
CMD ["gunicorn", "eld_logs.asgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--worker-connections", "1000", \
     "--max-requests", "10000", \
     "--max-requests-jitter", "1000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--capture-output", \
     "--enable-stdio-inheritance"]

# =============================================================================
# CELERY WORKER STAGE
# =============================================================================
FROM production AS celery-worker

CMD ["celery", "-A", "eld_logs", "worker", \
     "--loglevel=INFO", \
     "--concurrency=2", \
     "--queues=default,maps"]

# =============================================================================
# CELERY BEAT STAGE
# =============================================================================
FROM production AS celery-beat

CMD ["celery", "-A", "eld_logs", "beat", "--loglevel=INFO"]