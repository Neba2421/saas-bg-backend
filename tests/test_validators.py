"""
tests/test_validators.py
Tests for the upload validation pipeline.
"""

import io
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from fastapi import HTTPException

from services.validators import (
    validate_file_type,
    validate_file_size,
    validate_image_dimensions,
    validate_image_integrity,
)
from config.constants import (
    ALLOWED_TYPES,
    INVALID_FILE_TYPE,
    FILE_TOO_LARGE,
    INVALID_DIMENSIONS,
    INVALID_IMAGE,
)
from config.settings import MAX_FILE_SIZE, MAX_WIDTH, MAX_HEIGHT


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_upload_file(content_type: str, data: bytes, filename: str = "test.png"):
    """Create a mock UploadFile with content_type property."""
    file_obj = MagicMock()
    file_obj.filename = filename
    file_obj.content_type = content_type
    file_obj.file = io.BytesIO(data)
    return file_obj


def make_test_image(
    width: int = 100,
    height: int = 100,
    format: str = "PNG",
) -> bytes:
    """Create a valid test image and return its bytes."""
    img = Image.new("RGBA", (width, height), (128, 128, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


# ── 1. File Type Validation ───────────────────────────────────────────────────

class TestValidateFileType:
    """Tests for validate_file_type()."""

    @pytest.mark.parametrize("mime_type", ALLOWED_TYPES)
    def test_valid_file_type(self, mime_type):
        """Accept allowed MIME types."""
        data = make_test_image()
        file = make_upload_file(mime_type, data)
        # Should not raise
        validate_file_type(file)

    def test_invalid_file_type(self):
        """Reject disallowed MIME types."""
        data = b"not an image"
        file = make_upload_file("text/plain", data, "test.txt")
        with pytest.raises(HTTPException) as exc_info:
            validate_file_type(file)
        assert exc_info.value.status_code == 415
        assert exc_info.value.detail == INVALID_FILE_TYPE

    def test_pdf_rejected(self):
        """Reject PDF files."""
        data = b"%PDF-1.4 fake pdf"
        file = make_upload_file("application/pdf", data, "test.pdf")
        with pytest.raises(HTTPException) as exc_info:
            validate_file_type(file)
        assert exc_info.value.status_code == 415


# ── 2. File Size Validation ───────────────────────────────────────────────────

class TestValidateFileSize:
    """Tests for validate_file_size()."""

    def test_valid_file_size(self):
        """Accept files under MAX_FILE_SIZE."""
        data = b"x" * 1000  # 1 KB
        # Should not raise
        validate_file_size(data)

    def test_exact_max_size(self):
        """Accept files exactly at MAX_FILE_SIZE."""
        data = b"x" * MAX_FILE_SIZE
        # Should not raise
        validate_file_size(data)

    def test_oversized_file(self):
        """Reject files over MAX_FILE_SIZE."""
        data = b"x" * (MAX_FILE_SIZE + 1)
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(data)
        assert exc_info.value.status_code == 413
        assert exc_info.value.detail == FILE_TOO_LARGE

    def test_large_oversized_file(self):
        """Reject significantly oversized files."""
        data = b"x" * (10 * 1024 * 1024)  # 10 MB
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(data)
        assert exc_info.value.status_code == 413


# ── 3. Image Dimensions Validation ────────────────────────────────────────────

class TestValidateImageDimensions:
    """Tests for validate_image_dimensions()."""

    def test_valid_dimensions(self):
        """Accept images within limits."""
        img = Image.new("RGBA", (100, 100))
        # Should not raise
        validate_image_dimensions(img)

    def test_max_dimensions(self):
        """Accept images at exactly max dimensions."""
        img = Image.new("RGBA", (MAX_WIDTH, MAX_HEIGHT))
        # Should not raise
        validate_image_dimensions(img)

    def test_width_exceeds_limit(self):
        """Reject images wider than MAX_WIDTH."""
        img = Image.new("RGBA", (MAX_WIDTH + 1, 100))
        with pytest.raises(HTTPException) as exc_info:
            validate_image_dimensions(img)
        assert exc_info.value.status_code == 400
        assert INVALID_DIMENSIONS in exc_info.value.detail

    def test_height_exceeds_limit(self):
        """Reject images taller than MAX_HEIGHT."""
        img = Image.new("RGBA", (100, MAX_HEIGHT + 1))
        with pytest.raises(HTTPException) as exc_info:
            validate_image_dimensions(img)
        assert exc_info.value.status_code == 400

    def test_both_exceed_limit(self):
        """Reject images exceeding both limits."""
        img = Image.new("RGBA", (MAX_WIDTH + 1, MAX_HEIGHT + 1))
        with pytest.raises(HTTPException) as exc_info:
            validate_image_dimensions(img)
        assert exc_info.value.status_code == 400


# ── 4. Image Integrity Validation ─────────────────────────────────────────────

class TestValidateImageIntegrity:
    """Tests for validate_image_integrity()."""

    def test_valid_png(self):
        """Accept a valid PNG image."""
        data = make_test_image(format="PNG")
        result = validate_image_integrity(data)
        assert isinstance(result, Image.Image)
        assert result.mode == "RGBA"

    def test_valid_jpeg(self):
        """Accept a valid JPEG image."""
        img = Image.new("RGB", (100, 100), (128, 128, 128))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        data = buf.getvalue()
        result = validate_image_integrity(data)
        assert isinstance(result, Image.Image)

    def test_corrupted_image(self):
        """Reject corrupted data."""
        data = b"not an image at all"
        with pytest.raises(HTTPException) as exc_info:
            validate_image_integrity(data)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == INVALID_IMAGE

    def test_truncated_image(self):
        """Reject truncated image data."""
        # Create a valid image but truncate it
        data = make_test_image()
        truncated = data[:len(data) // 2]
        with pytest.raises(HTTPException) as exc_info:
            validate_image_integrity(truncated)
        assert exc_info.value.status_code == 400

    def test_empty_data(self):
        """Reject empty data."""
        with pytest.raises(HTTPException) as exc_info:
            validate_image_integrity(b"")
        assert exc_info.value.status_code == 400