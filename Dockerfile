# -*- coding: utf-8 -*-
# Multi-stage Dockerfile for production deployment
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl \\
    git \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# =============================================================================
# Stage 1: Dependencies
# =============================================================================
FROM base as dependencies

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional production dependencies
RUN pip install --no-cache-dir \\
    gunicorn>=21.0.0 \\
    httpx>=0.25.0

# =============================================================================
# Stage 2: Application
# =============================================================================
FROM base as application

# Copy installed dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \\
    useradd --uid 1000 --gid appgroup --shell /bin/bash appuser

# Create data directories
RUN mkdir -p /app/data/{raw,graph,embeddings} && \\
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health/live || exit 1

# Default command (can be overridden)
CMD [\"python\", \"-m\", \"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]

# =============================================================================
# Development stage (default)
# =============================================================================
FROM base as development

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run with hot reload for development
CMD [\"python\", \"-m\", \"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\", \"--reload\"]