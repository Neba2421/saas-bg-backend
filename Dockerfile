# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Builder
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libgl1 \
        libglib2.0-0 \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip wheel

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Runtime (Updated for Hugging Face Spaces)
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create user with UID 1000 (Hugging Face requirement)
RUN useradd -m -u 1000 appuser && \
    addgroup appgroup && \
    usermod -a -G appgroup appuser

WORKDIR /home/appuser/app

# Copy installed packages from builder
COPY --from=builder --chown=appuser:appgroup /install /usr/local

# Reinstall packaging in runtime stage
RUN pip install --no-cache-dir packaging

# Copy application source
COPY --chown=appuser:appgroup . .

USER appuser

# Create cache directories
RUN mkdir -p /tmp/numba_cache /tmp/rembg_cache

ENV NUMBA_CACHE_DIR=/tmp/numba_cache
ENV U2NET_HOME=/tmp/rembg_cache

ENV ORT_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    WEB_CONCURRENCY=1 \
    UVICORN_LIMIT_CONCURRENCY=25 \
    MAX_FILE_SIZE=5242880 \
    MAX_WIDTH=6000 \
    MAX_HEIGHT=6000 \
    PORT=7860

# Hugging Face default port
EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python healthcheck.py

# Run with uvicorn (better for Hugging Face than gunicorn)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]