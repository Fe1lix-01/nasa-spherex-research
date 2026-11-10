import pytest

from astropy.io import fits
from fastapi.testclient import TestClient

from app.main import app
from app.services import frames as frames_service
# BytesIO permite abrir imágenes PNG directamente desde memoria.
from io import BytesIO

# Pillow permite verificar el contenido y las dimensiones del PNG.
from PIL import Image

# Importamos el servicio para poder modificar su directorio durante las pruebas.
from app.services import frame_images as frame_images_service


client = TestClient(app)


def test_get_frames():
    response = client.get("/api/v1/frames")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 6
    assert len(data["frames"]) == 6

    detectors = {
        frame["detector"]
        for frame in data["frames"]
    }

    assert detectors == {
        "D1", "D2", "D3",
        "D4", "D5", "D6"
    }

    for frame in data["frames"]:
        assert frame["width"] == 16
        assert frame["height"] == 16

        assert 0.02 < frame["fov_x_deg"] < 0.04
        assert 0.02 < frame["fov_y_deg"] < 0.04

        assert 24.0 < frame["center_ra_deg"] < 25.0
        assert 9.0 < frame["center_dec_deg"] < 10.0

        assert frame["coordinate_system"] == "ICRS"
        assert frame["projection"] == "TAN"


def test_list_frames_missing_directory(monkeypatch, tmp_path):
    missing_dir = tmp_path / "missing"

    monkeypatch.setattr(
        frames_service,
        "FITS_DIR",
        missing_dir
    )

    with pytest.raises(FileNotFoundError):
        frames_service.list_frames()


def test_list_frames_rejects_fits_without_wcs(
    monkeypatch,
    tmp_path
):
    fits_dir = tmp_path / "fits"
    fits_dir.mkdir()

    invalid_file = fits_dir / "test_D1_100_arcsec_cutout.fits"

    hdu = fits.PrimaryHDU(
        data=[[0.0] * 16 for _ in range(16)]
    )

    hdu.writeto(invalid_file)

    monkeypatch.setattr(
        frames_service,
        "FITS_DIR",
        fits_dir
    )

    with pytest.raises(
        frames_service.FrameMetadataError,
        match="WCS"
    ):
        frames_service.list_frames()

def test_get_frame_image_returns_png():
    """Comprueba que un FITS válido se entregue como imagen PNG."""

    # Recuperamos el identificador de un frame existente.
    frame_id = frames_service.list_frames()[0]["id"]

    # Solicitamos la representación PNG del frame.
    response = client.get(f"/api/v1/frames/{frame_id}/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Abrimos la imagen directamente desde la respuesta HTTP.
    with Image.open(BytesIO(response.content)) as image:
        assert image.format == "PNG"
        assert image.mode == "L"
        assert image.size == (16, 16)


def test_get_frame_image_not_found():
    """Comprueba que un frame inexistente devuelva HTTP 404."""

    response = client.get(
        "/api/v1/frames/frame_inexistente_D1.fits/image"
    )

    assert response.status_code == 404


def test_get_frame_image_rejects_invalid_fits(monkeypatch, tmp_path):
    """Comprueba que un archivo que no es FITS devuelva HTTP 503."""

    # Creamos un directorio temporal para aislar la prueba.
    fits_dir = tmp_path / "fits"
    fits_dir.mkdir()

    # Creamos un archivo que no contiene una estructura FITS válida.
    invalid_file = fits_dir / "invalid_D1.fits"
    invalid_file.write_bytes(b"Esto no es un archivo FITS")

    # Redirigimos el servicio al directorio temporal.
    monkeypatch.setattr(
        frame_images_service,
        "FITS_DIR",
        fits_dir,
    )

    # Solicitamos la conversión del archivo inválido.
    response = client.get(
        "/api/v1/frames/invalid_D1.fits/image"
    )

    assert response.status_code == 503


def test_get_frame_image_rejects_non_finite_data(monkeypatch, tmp_path):
    """Comprueba que una imagen sin valores finitos no pueda convertirse."""

    # Creamos un directorio temporal.
    fits_dir = tmp_path / "fits"
    fits_dir.mkdir()

    # Generamos una matriz cuyos píxeles contienen únicamente NaN.
    invalid_file = fits_dir / "nan_D1.fits"

    hdu = fits.PrimaryHDU(
        data=[
            [float("nan") for _ in range(16)]
            for _ in range(16)
        ]
    )

    hdu.writeto(invalid_file)

    # Redirigimos el servicio al directorio temporal.
    monkeypatch.setattr(
        frame_images_service,
        "FITS_DIR",
        fits_dir,
    )

    # Solicitamos la conversión de la imagen sin valores válidos.
    response = client.get(
        "/api/v1/frames/nan_D1.fits/image"
    )

    assert response.status_code == 503
