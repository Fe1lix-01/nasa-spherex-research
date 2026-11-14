import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import observations as observations_service
from app.services import remote_catalog as remote_catalog_service
from app.services.objects import make_object_id

from io import BytesIO

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from PIL import Image

from app.clients.irsa import IrsaResponseError
from app.services.remote_previews import render_cutout_png


@pytest.fixture
def catalogo_local_temporal(tmp_path, monkeypatch):
    fits_dir = tmp_path / "fits"
    fits_dir.mkdir()

    # Archivo utilizado únicamente para la enumeración del catálogo.
    # Estas pruebas no procesan sus píxeles.
    (fits_dir / "M101_D1_test.fits").touch()

    monkeypatch.setattr(
        observations_service,
        "FITS_DIR",
        fits_dir,
    )
    monkeypatch.setattr(
        remote_catalog_service,
        "M101_METADATA_PATH",
        tmp_path / "registro_ausente.json",
    )

    return make_object_id("M101")


def test_objeto_inexistente_devuelve_404(catalogo_local_temporal):
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/objects/no-existe/remote-preview",
            params={"product_id": "ivo://example/product"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "El objeto o producto remoto no está registrado"
    )


def test_producto_no_registrado_devuelve_404(catalogo_local_temporal):
    object_id = catalogo_local_temporal

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/objects/{object_id}/remote-preview",
            params={"product_id": "ivo://example/product"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "El objeto o producto remoto no está registrado"
    )


@pytest.mark.parametrize("params", [{}, {"product_id": ""}])
def test_producto_obligatorio_devuelve_422(
    catalogo_local_temporal,
    params,
):
    object_id = catalogo_local_temporal

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/objects/{object_id}/remote-preview",
            params=params,
        )

    assert response.status_code == 422

def crear_recorte_sintetico(caso="valido"):
    """Crea bytes FITS para probar la lectura y el WCS."""
    if caso == "archivo_corrupto":
        return b"contenido que no es FITS"

    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [3, 3]
    wcs.wcs.cdelt = [-0.001, 0.001]
    wcs.wcs.crval = [210.8, 54.3]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]

    header = wcs.to_header()
    header["BUNIT"] = "MJy/sr"

    data = np.arange(25, dtype=float).reshape(5, 5)

    if caso == "imagen_vacia":
        data = None
    elif caso == "imagen_3d":
        data = np.ones((2, 5, 5))
    elif caso == "sin_wcs":
        header = fits.Header()
    elif caso == "sin_datos_finitos":
        data[:] = np.nan

    hdus = [fits.PrimaryHDU()]

    if caso != "sin_image":
        hdus.append(
            fits.ImageHDU(
                data=data,
                header=header,
                name="IMAGE",
            )
        )

    output = BytesIO()

    with fits.HDUList(hdus) as hdul:
        hdul.writeto(output)

    return output.getvalue()


def test_recorte_valido_genera_png():
    content = crear_recorte_sintetico()

    png = render_cutout_png(content, ra=210.8, dec=54.3)

    assert png.startswith(b"\x89PNG\r\n\x1a\n")

    with Image.open(BytesIO(png)) as image:
        assert image.format == "PNG"
        assert image.size == (5, 5)
        image.verify()

    with Image.open(BytesIO(png)) as image:
        image.load()


@pytest.mark.parametrize(
    "caso",
    [
        "archivo_corrupto",
        "sin_image",
        "imagen_vacia",
        "imagen_3d",
        "sin_wcs",
        "sin_datos_finitos",
        "posicion_fuera",
    ],
)
def test_recorte_invalido_rechazado(caso):
    content = crear_recorte_sintetico(caso)

    # Esta posición queda fuera de la imagen sintética.
    ra = 220.0 if caso == "posicion_fuera" else 210.8

    with pytest.raises(
        IrsaResponseError,
        match="No fue posible interpretar",
    ):
        render_cutout_png(content, ra=ra, dec=54.3)