# NatLangChain Dockerfile
# Multi-stage build for optimal image size

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

# Install Python dependencies with hash verification (Finding 3.1)
COPY requirements-lock.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-lock.txt

# SECURITY: Pre-download ML model during build to avoid runtime downloads (Finding 3.2)
ENV SENTENCE_TRANSFORMERS_HOME=/opt/models
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.11-slim as runtime

# Security: Create non-root user
RUN groupadd --gid 1000 natlang && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home natlang

WORKDIR /app

# Copy virtual environment and pre-downloaded models from builder
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/models /opt/models
ENV PATH="/opt/venv/bin:$PATH"
ENV SENTENCE_TRANSFORMERS_HOME=/opt/models

# Copy application code
COPY --chown=natlang:natlang src/ ./src/
COPY --chown=natlang:natlang run_server.py .

# Create data directory for chain persistence
RUN mkdir -p /app/data && \
    chown -R natlang:natlang /app/data

# Run as non-root
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

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Run the server
CMD ["python", "run_server.py"]
