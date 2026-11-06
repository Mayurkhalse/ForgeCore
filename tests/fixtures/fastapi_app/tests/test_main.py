"""Unit tests for sample FastAPI app."""
from __future__ import annotations

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """Verifies that GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
