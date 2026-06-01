"""
Tests for background removal endpoint.
"""

import pytest
import io
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient

# Patch model loading before importing app
with patch("app.load_model"), \
     patch("app.warm_model"), \
     patch("app.is_model_ready", return_value=True):
    from app import app

client = TestClient(app)


def create_test_image(
    width: int = 100,
    height: int = 100,
    format: str = "PNG",
    mode: str = "RGB",
) -> bytes:
    """Create a valid test image and return its bytes."""
    img = Image.new(mode, (width, height))
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


class TestRemoveBackgroundEndpoint:
    """Tests for the background removal endpoint."""

    def test_remove_background_valid_png(self):
        """Successfully process a valid PNG image."""
        image_data = create_test_image(format="PNG")
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.png", io.BytesIO(image_data), "image/png")},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        assert len(response.content) > 0

    def test_remove_background_valid_jpeg(self):
        """Successfully process a valid JPEG image."""
        image_data = create_test_image(format="JPEG", mode="RGB")
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.jpg", io.BytesIO(image_data), "image/jpeg")},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_remove_background_valid_webp(self):
        """Successfully process a valid WEBP image."""
        image_data = create_test_image(format="WEBP")
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.webp", io.BytesIO(image_data), "image/webp")},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_remove_background_unsupported_mime_type(self):
        """Reject files with unsupported MIME types."""
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
        )
        assert response.status_code == 415
        data = response.json()
        assert "detail" in data
        assert "Unsupported" in data["detail"]

    def test_remove_background_pdf_rejected(self):
        """Reject PDF files even with correct extension."""
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")},
        )
        assert response.status_code == 415

    def test_remove_background_corrupted_image(self):
        """Reject corrupted image data."""
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.png", io.BytesIO(b"corrupted data"), "image/png")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_remove_background_oversized_file(self):
        """Reject files exceeding size limit (5 MB)."""
        oversized_data = b"x" * (6 * 1024 * 1024)  # 6 MB
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.png", io.BytesIO(oversized_data), "image/png")},
        )
        assert response.status_code == 413
        data = response.json()
        assert "5 MB" in data["detail"]

    def test_remove_background_invalid_dimensions(self):
        """Reject images exceeding dimension limits (6000x6000)."""
        oversized_image = create_test_image(width=7000, height=100)
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.png", io.BytesIO(oversized_image), "image/png")},
        )
        assert response.status_code == 400
        data = response.json()
        assert "dimensions" in data["detail"].lower() or "exceed" in data["detail"].lower()

    def test_remove_background_missing_file(self):
        """Reject requests without file."""
        response = client.post("/api/v1/remove-background")
        assert response.status_code == 422

    @patch("app.remove_background")
    def test_remove_background_model_processing_error(self, mock_remove):
        """Handle model inference errors gracefully."""
        from fastapi import HTTPException
        mock_remove.side_effect = HTTPException(status_code=500, detail="Processing failed")

        image_data = create_test_image(format="PNG")
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.png", io.BytesIO(image_data), "image/png")},
        )
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    def test_response_headers_correct(self):
        """Verify response headers are correct."""
        image_data = create_test_image(format="PNG")
        response = client.post(
            "/api/v1/remove-background",
            files={"file": ("test.png", io.BytesIO(image_data), "image/png")},
        )
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "result.png" in response.headers["content-disposition"]
        assert "X-Engine" in response.headers