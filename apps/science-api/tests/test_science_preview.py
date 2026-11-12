import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


ENDPOINT = "/api/v1/science/m101/channel-63/preview"


def test_m101_preview_serves_png():
    """Integración que requiere el FITS real configurado localmente."""
    fits_path = os.environ.get("M101_FITS_PATH")

    if not fits_path or not Path(fits_path).is_file():
        pytest.skip("Configura M101_FITS_PATH con el FITS local de M101")

    with TestClient(app) as client:
        response = client.get(ENDPOINT)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")


def test_m101_preview_without_configuration(monkeypatch):
    monkeypatch.delenv("M101_FITS_PATH", raising=False)

    with TestClient(app) as client:
        response = client.get(ENDPOINT)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El archivo científico de M101 no está configurado"
    )


def test_m101_preview_unavailable(tmp_path, monkeypatch):
    missing_fits = tmp_path / "missing.fits"
    monkeypatch.setenv("M101_FITS_PATH", str(missing_fits))

    with TestClient(app) as client:
        response = client.get(ENDPOINT)

    assert response.status_code == 503
    assert str(tmp_path) not in response.text


def test_m101_preview_invalid_fits(tmp_path, monkeypatch):
    invalid_fits = tmp_path / "invalid.fits"
    invalid_fits.write_bytes(b"archivo FITS invalido")

    monkeypatch.setenv("M101_FITS_PATH", str(invalid_fits))

    with TestClient(app) as client:
        response = client.get(ENDPOINT)

    assert response.status_code == 503
    assert str(tmp_path) not in response.text