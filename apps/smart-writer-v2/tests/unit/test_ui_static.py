"""GET / serves the Next static export when app/static/ui is present."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.entrypoints.http import UI_STATIC_DIR, app


def test_ui_index_served_when_built() -> None:
    index = UI_STATIC_DIR / "index.html"
    if not index.is_file():
        # Fresh clone without build:fastapi — skip rather than invent assets.
        return
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Smart Writer" in response.text or "<!DOCTYPE html>" in response.text.lower()


def test_health_still_public_with_ui_mount() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_ui_static_dir_constant() -> None:
    assert UI_STATIC_DIR == Path(__file__).resolve().parents[2] / "app" / "static" / "ui"
