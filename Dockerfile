# NatLangChain Dockerfile
# Multi-stage build for optimal image size
#
# Security Enforcement Modes:
# - Standard: Run as non-root (default, detection-only security)
# - Privileged: Run with capabilities (full enforcement features)
#
# For full security enforcement, run with:
#   docker run --cap-add=NET_ADMIN --cap-add=SYS_ADMIN natlangchain
#
# Or use docker-compose.security.yml for pre-configured secure deployment

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.11-slim as runtime

# Install security enforcement tools (optional, for full enforcement mode)
# These are only useful when running with elevated capabilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    iptables \
    iproute2 \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root user
RUN groupadd --gid 1000 natlang && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home natlang

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=natlang:natlang src/ ./src/
COPY --chown=natlang:natlang config/ ./config/
COPY --chown=natlang:natlang run_server.py .

# Create data and log directories for persistence
RUN mkdir -p /app/data /var/log/natlangchain && \
    chown -R natlang:natlang /app/data /var/log/natlangchain

# By default, run as non-root (detection-only mode)
# For enforcement mode, override with USER root in docker-compose
USER natlang

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=5000 \
    CHAIN_DATA_FILE=/app/data/chain_data.json \
    FLASK_DEBUG=false

# Expose API port
EXPOSE 5000

# Health check (uses Kubernetes-compatible liveness endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health/live')" || exit 1

# Run the server
CMD ["python", "run_server.py"]
