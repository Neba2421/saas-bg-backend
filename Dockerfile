# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Builder
# Install Python packages and pre-download the Silueta ONNX model.
# Keeping this separate from the runtime stage avoids shipping build tooling
# and intermediate cache layers into production.
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /build

# System build deps (for Pillow C extensions, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into an isolated prefix.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Pre-download the Silueta ONNX model so it's baked into the image
# and the container never needs outbound model downloads at runtime.
RUN REMBG_CACHE=/install/lib/python3.11/site-packages/rembg/sessions \
    python -c "from rembg import new_session; new_session('silueta')"


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Runtime
# Minimal image: only the installed packages + app code.
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

# Runtime-only system libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copy installed packages from builder.
COPY --from=builder /install /usr/local

# Copy application source.
COPY --chown=appuser:appgroup . .

USER appuser

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
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
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
