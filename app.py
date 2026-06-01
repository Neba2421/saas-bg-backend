"""
app.py
Main FastAPI application — background removal SaaS backend.

Routes
------
  GET  /                          → service info
  GET  /health                    → model health probe (used by Docker + Render)
  POST /api/v1/remove-background  → background removal endpoint
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.exceptions import RequestValidationError

from config.constants import ENGINE_TAG, API_VERSION
from config.settings import ALLOWED_ORIGINS
from models.schemas import HealthResponse, RootResponse
from services.image_processor import (
    load_model,
    warm_model,
    is_model_ready,
    remove_background,
    image_to_png_buffer,
)
from services.validators import run_all_validations

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Startup / Shutdown lifecycle ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    logger.info("=== Background Remover API starting ===")
    load_model()
    warm_model()
    logger.info("=== API ready — accepting requests ===")
    yield
    # --- shutdown ---
    logger.info("=== Background Remover API shutting down ===")


# ── Application factory ────────────────────────────────────────────────────────

app = FastAPI(
    title="Background Remover API",
    version=API_VERSION,
    description="Remove image backgrounds in under a second using the Silueta ONNX model.",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Exception Handlers ─────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    """Handle validation errors with a clean JSON response."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request payload."
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    """Catch-all for unexpected errors."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error."
        },
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_model=RootResponse, tags=["Meta"])
async def root():
    """Service identity endpoint."""
    return RootResponse()


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
async def health():
    """
    Docker & Render health probe.

    Returns 200 when the model is loaded and ready.
    Returns 503 if the inference engine failed to initialise.
    """
    from fastapi import HTTPException
    from config.constants import MODEL_UNAVAILABLE

    if not is_model_ready():
        raise HTTPException(status_code=503, detail=MODEL_UNAVAILABLE)

    return HealthResponse(
        status="healthy",
        engine=ENGINE_TAG,
        model_loaded=True,
    )


@app.post(
    "/api/v1/remove-background",
    tags=["Processing"],
    responses={
        200: {"content": {"image/png": {}}, "description": "Transparent PNG stream"},
        400: {"description": "Corrupted image / bad dimensions"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported file type"},
        500: {"description": "Model processing failure"},
        503: {"description": "Inference engine unavailable"},
    },
)
async def remove_background_endpoint(
    file: UploadFile = File(..., description="JPEG, PNG, or WEBP image ≤ 5 MB"),
):
    """
    Accept an image upload and return a transparent PNG.

    Processing pipeline
    -------------------
      1. Validate MIME type
      2. Read bytes → validate size
      3. Decode with Pillow → validate dimensions + integrity
      4. Run rembg Silueta inference
      5. Encode result to PNG
      6. Stream to client (no disk I/O)
    """
    logger.info("Request received: %s (%s)", file.filename, file.content_type)

    # ── Validation ─────────────────────────────────────────────────────────────
    _raw_bytes, image = await run_all_validations(file)
    logger.info("Validation passed for %s", file.filename)

    # ── Inference ──────────────────────────────────────────────────────────────
    logger.info("Processing started.")
    result_image = remove_background(image)
    logger.info("Processing complete.")

    # ── Export ─────────────────────────────────────────────────────────────────
    png_buffer = image_to_png_buffer(result_image)

    return StreamingResponse(
        png_buffer,
        media_type="image/png",
        headers={
            "Content-Disposition": 'attachment; filename="result.png"',
            "X-Engine": ENGINE_TAG,
        },
    )
