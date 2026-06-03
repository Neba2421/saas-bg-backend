# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Builder
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /build

# Build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libgl1 \
        libglib2.0-0 \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip wheel

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Runtime
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

# Runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=appuser:appgroup . .

USER appuser

# Create cache directories
RUN mkdir -p /tmp/numba_cache /tmp/rembg_cache

# Set cache directories to avoid numba errors
ENV NUMBA_CACHE_DIR=/tmp/numba_cache
ENV U2NET_HOME=/tmp/rembg_cache

# Environment defaults
ENV ORT_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    WEB_CONCURRENCY=4 \
    UVICORN_LIMIT_CONCURRENCY=50 \
    MAX_FILE_SIZE=5242880 \
    MAX_WIDTH=6000 \
    MAX_HEIGHT=6000 \
    PORT=8000

EXPOSE 8000

# Health check with longer start period for model download
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python healthcheck.py

# Start gunicorn
CMD gunicorn app:app \
    --workers ${WEB_CONCURRENCY} \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:${PORT} \
    --preload \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 120 \
    --graceful-timeout 30 \
    --log-level info