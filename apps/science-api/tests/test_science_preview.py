from fastapi.testclient import TestClient

from app.main import app
from app.routers import science_preview


def test_m101_preview_serves_png():
    with TestClient(app) as client:
        response = client.get("/api/v1/science/m101/channel-63/preview")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_m101_preview_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(science_preview, "M101_PREVIEW", tmp_path / "missing.png")
    with TestClient(app) as client:
        response = client.get("/api/v1/science/m101/channel-63/preview")
    assert response.status_code == 503
    assert str(tmp_path) not in response.text
