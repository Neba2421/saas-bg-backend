"""
tests/test_root.py
Tests for the root endpoint.
"""

from fastapi.testclient import TestClient
from unittest.mock import patch

# Patch model loading so tests run without the ONNX binary present.
with patch("app.load_model"), \
     patch("app.warm_model"), \
     patch("app.is_model_ready", return_value=True):
    from app import app

client = TestClient(app)


def test_root():
    """Test the root endpoint returns correct service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Background Remover API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "running"


def test_root_content_type():
    """Test the root endpoint returns JSON."""
    response = client.get("/")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]