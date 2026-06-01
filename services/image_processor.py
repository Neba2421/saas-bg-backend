"""
services/image_processor.py
Central AI engine — Silueta ONNX model via rembg.

Lifecycle
---------
  startup  → load_model()  → warm_model()  → ready = True
  request  → remove_background()  → image_to_png_buffer()
  shutdown → (session GC'd automatically)

Design decisions
----------------
  * The rembg session is stored as a module-level singleton so it is
    created exactly once per Gunicorn worker process.
  * warm_model() runs a dummy inference so the first real request
    doesn't pay the ONNX JIT cost.
  * We never touch disk — all I/O is in-memory BytesIO.
"""

import logging
from io import BytesIO

from PIL import Image
from rembg import new_session, remove

from config.constants import MODEL_NAME, ENGINE_TAG, PROCESSING_FAILED
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ── Module-level state ─────────────────────────────────────────────────────────
_session = None          # rembg InferenceSession
_model_ready: bool = False


# ── Startup ────────────────────────────────────────────────────────────────────

def load_model() -> None:
    """
    Instantiate the rembg Silueta session.
    Must be called once during FastAPI startup before any request is served.
    """
    global _session, _model_ready
    logger.info("Loading %s model…", ENGINE_TAG)
    try:
        _session = new_session(MODEL_NAME)
        _model_ready = True
        logger.info("Model loaded successfully.")
    except Exception as exc:
        _model_ready = False
        logger.error("Model load failed: %s", exc)
        raise


def warm_model() -> None:
    """
    Run one dummy inference to prime ONNX caches.
    This prevents the first real user request from experiencing cold-start latency.
    """
    if not _model_ready:
        logger.warning("Skipping warmup — model not loaded.")
        return
    logger.info("Warming up model…")
    try:
        dummy = Image.new("RGBA", (64, 64), (128, 128, 128, 255))
        _run_inference(dummy)
        logger.info("Warmup complete.")
    except Exception as exc:
        logger.warning("Warmup inference failed (non-fatal): %s", exc)


# ── Status ─────────────────────────────────────────────────────────────────────

def is_model_ready() -> bool:
    """Return True when the session is loaded and warmup has run."""
    return _model_ready


# ── Core inference ─────────────────────────────────────────────────────────────

def _run_inference(image: Image.Image) -> Image.Image:
    """Internal: run rembg remove() with the preloaded session."""
    return remove(image, session=_session)


def remove_background(image: Image.Image) -> Image.Image:
    """
    Public API: accept a PIL Image, return a transparent RGBA PIL Image.
    Raises HTTPException(500) on model failure.
    """
    if not _model_ready:
        raise HTTPException(status_code=503, detail="Inference engine unavailable.")
    try:
        logger.info("Processing image %dx%d…", *image.size)
        result = _run_inference(image)
        logger.info("Processing complete.")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Background removal failed: %s", exc)
        raise HTTPException(status_code=500, detail=PROCESSING_FAILED)


# ── Export ─────────────────────────────────────────────────────────────────────

def image_to_png_buffer(image: Image.Image) -> BytesIO:
    """
    Serialize a PIL Image to an in-memory PNG BytesIO stream.
    The caller is responsible for streaming this buffer to the client.
    """
    buf = BytesIO()
    image.save(buf, format="PNG", optimize=False)
    buf.seek(0)
    return buf
