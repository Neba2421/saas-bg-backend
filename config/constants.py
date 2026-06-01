"""
config/constants.py
Immutable application constants.
Import from here; never define magic strings in business logic.
"""

# ── Allowed MIME types ─────────────────────────────────────────────────────────
ALLOWED_TYPES: list[str] = [
    "image/jpeg",
    "image/png",
    "image/webp",
]

# ── User-facing error messages ─────────────────────────────────────────────────
INVALID_FILE_TYPE  = "Unsupported image format. Please upload a JPEG, PNG, or WEBP file."
FILE_TOO_LARGE     = "File exceeds the 5 MB upload limit. Please compress the image and try again."
INVALID_DIMENSIONS = "Image dimensions exceed the 6000×6000 pixel limit."
INVALID_IMAGE      = "The uploaded file appears to be corrupted or is not a valid image."
PROCESSING_FAILED  = "Background removal failed. Please try again with a different image."
MODEL_UNAVAILABLE  = "The inference engine is currently unavailable. Please try again shortly."

# ── API version ────────────────────────────────────────────────────────────────
API_VERSION = "1.0.0"

# ── Model identifiers ──────────────────────────────────────────────────────────
MODEL_NAME = "silueta"          # rembg session key
ENGINE_TAG = "rembg-silueta"   # reported in /health
