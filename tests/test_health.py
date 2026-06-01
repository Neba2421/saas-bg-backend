"""
tests/test_health.py
Sprint 1 — verify the API scaffolding works before the model is added.
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
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "version" in data


def test_health_when_model_ready():
    with patch("app.is_model_ready", return_value=True):
        response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True


def test_health_when_model_not_ready():
    with patch("app.is_model_ready", return_value=False):
        response = client.get("/health")
    assert response.status_code == 503
