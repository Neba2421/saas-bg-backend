"""
services/validators.py
Four-layer upload protection gate.

Call order enforced by the route handler:
  1. validate_file_type()       — reject non-images early (before reading bytes)
  2. validate_file_size()       — reject oversized uploads
  3. validate_image_dimensions() — reject resolution bombs
  4. validate_image_integrity()  — reject corrupted files
"""

from io import BytesIO
from typing import Tuple

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

# ── Security: Protect against decompression bomb attacks ──────────────────────
# Limit image to 50 megapixels to prevent memory exhaustion
Image.MAX_IMAGE_PIXELS = 50_000_000

from config.constants import (
    ALLOWED_TYPES,
    INVALID_FILE_TYPE,
    FILE_TOO_LARGE,
    INVALID_DIMENSIONS,
    INVALID_IMAGE,
)
from config.settings import MAX_FILE_SIZE, MAX_WIDTH, MAX_HEIGHT


# ── 1. MIME type ───────────────────────────────────────────────────────────────

def validate_file_type(file: UploadFile) -> None:
    """Reject files whose Content-Type is not in the allowed list."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail=INVALID_FILE_TYPE)


# ── 2. File size ───────────────────────────────────────────────────────────────

def validate_file_size(data: bytes) -> None:
    """Reject payloads larger than MAX_FILE_SIZE bytes."""
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=FILE_TOO_LARGE)


# ── 3. Image dimensions ────────────────────────────────────────────────────────

def validate_image_dimensions(image: Image.Image) -> None:
    """Reject images wider or taller than the configured maximum."""
    width, height = image.size
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        raise HTTPException(
            status_code=400,
            detail=f"{INVALID_DIMENSIONS} (received {width}×{height})",
        )


# ── 4. Image integrity ─────────────────────────────────────────────────────────

def validate_image_integrity(data: bytes) -> Image.Image:
    """
    Attempt to fully decode the image data.
    Returns the PIL Image on success so the caller doesn't re-open it.
    Raises 400 if the file is corrupted or unrecognised.
    """
    try:
        image = Image.open(BytesIO(data))
        image.verify()                    # detects truncated / corrupted files
        # Re-open after verify() — Pillow closes the internal stream.
        image = Image.open(BytesIO(data)).convert("RGBA")
        return image
    except (UnidentifiedImageError, Exception):
        raise HTTPException(status_code=400, detail=INVALID_IMAGE)


# ── Convenience: run the full chain ───────────────────────────────────────────

async def run_all_validations(file: UploadFile) -> tuple[bytes, Image.Image]:
    """
    Execute every validation step and return (raw_bytes, pil_image).
    Raises HTTPException at the first failure.
    """
    validate_file_type(file)

    data: bytes = await file.read()

    validate_file_size(data)
    image = validate_image_integrity(data)
    validate_image_dimensions(image)

    return data, image
