"""GET /health is public and does not require OpenAI or the preview secret."""

from fastapi.testclient import TestClient

from app.entrypoints.http import app


def test_health_returns_200() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
