# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Builder
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /build

# Add build dependencies needed for pymatting, numpy, and scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libgl1 \
        libglib2.0-0 \
        libatlas-base-dev \
        liblapack-dev \
        libblas-dev \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel support
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install Python dependencies into an isolated prefix.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Runtime
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

# Install runtime libraries (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libatlas-base-dev \
        liblapack-dev \
        libblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages from builder.
COPY --from=builder /install /usr/local

# Copy application source.
COPY --chown=appuser:appgroup . .

USER appuser

# Tell rembg where to cache the model (writable location for non-root user)
ENV U2NET_HOME=/tmp/rembg_cache

# ── Environment defaults (overridden by Render environment variables) ──────────
ENV ORT_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    WEB_CONCURRENCY=4 \
    UVICORN_LIMIT_CONCURRENCY=50 \
    MAX_FILE_SIZE=5242880 \
    MAX_WIDTH=6000 \
    MAX_HEIGHT=6000 \
    PORT=8000

EXPOSE 8000

# Docker health check — runs every 30 s, 3 failures = unhealthy.
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python healthcheck.py

# ── Gunicorn: 4 UvicornWorkers, memory recycled every 1000 requests ───────────
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