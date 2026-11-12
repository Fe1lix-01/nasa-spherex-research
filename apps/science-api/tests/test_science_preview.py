from io import BytesIO

import numpy as np
import pytest
from astropy.io import fits
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.m101 import crear_mascara_m101, generar_figura_m101


ENDPOINT = "/api/v1/science/m101/channel-63/preview"


@pytest.fixture
def crear_fits(tmp_path):
    """Crea un FITS pequeño que podemos modificar en cada prueba."""

    def crear(
        *,
        canales=63,
        omitir=None,
        dimensiones_incompatibles=False,
        imagen_2d=False,
        filas_espectrales=None,
        columna="WAVELENGTH",
        longitud_onda=3.293,
    ):
        forma = (canales, 4, 4)

        imagen = np.arange(
            canales * 4 * 4,
            dtype=np.float32,
        ).reshape(forma) + 1

        if imagen_2d:
            imagen = imagen[0]

        forma_hits = (
            (canales, 3, 4)
            if dimensiones_incompatibles
            else forma
        )

        hits = np.ones(forma_hits, dtype=np.int32)
        flags = np.zeros(forma, dtype=np.int32)

        if filas_espectrales is None:
            filas_espectrales = canales

        wavelengths = np.full(
            filas_espectrales,
            longitud_onda,
            dtype=np.float64,
        )

        tabla = fits.BinTableHDU.from_columns(
            [
                fits.Column(
                    name=columna,
                    format="D",
                    array=wavelengths,
                )
            ],
            name="SPECTRAL_CHANNELS",
        )

        extensiones = [
            fits.ImageHDU(imagen, name="IMAGE"),
            fits.ImageHDU(hits, name="NHITS"),
            fits.ImageHDU(flags, name="FLAGS"),
            tabla,
        ]

        hdul = fits.HDUList(
            [fits.PrimaryHDU()]
            + [
                extension
                for extension in extensiones
                if extension.name != omitir
            ]
        )

        ruta = tmp_path / "m101_sintetico.fits"

        with hdul:
            hdul.writeto(ruta, overwrite=True)

        return ruta

    return crear


def comprobar_png(contenido):
    """Comprueba la firma, el formato y la decodificación del PNG."""
    assert contenido.startswith(b"\x89PNG\r\n\x1a\n")

    with Image.open(BytesIO(contenido)) as imagen:
        assert imagen.format == "PNG"
        assert imagen.width > 0
        assert imagen.height > 0
        imagen.verify()

    with Image.open(BytesIO(contenido)) as imagen:
        imagen.load()


def test_generar_figura_desde_fits_sintetico(crear_fits, tmp_path):
    archivo = crear_fits()
    salida = tmp_path / "figuras" / "canal_63.png"

    generar_figura_m101(archivo, salida, canal=63)

    assert salida.is_file()
    comprobar_png(salida.read_bytes())


def test_m101_preview_serves_png(crear_fits, monkeypatch):
    archivo = crear_fits()
    monkeypatch.setenv("M101_FITS_PATH", str(archivo))

    with TestClient(app) as client:
        response = client.get(ENDPOINT)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    comprobar_png(response.content)


@pytest.mark.parametrize(
    ("opciones", "mensaje"),
    [
        ({"omitir": "IMAGE"}, "extensiones requeridas"),
        ({"omitir": "NHITS"}, "extensiones requeridas"),
        ({"omitir": "FLAGS"}, "extensiones requeridas"),
        ({"omitir": "SPECTRAL_CHANNELS"}, "extensiones requeridas"),
        ({"dimensiones_incompatibles": True}, "mismas dimensiones"),
        ({"imagen_2d": True}, "tres dimensiones"),
        ({"canales": 62}, "no existe"),
        ({"filas_espectrales": 62}, "no contiene información"),
        ({"columna": "OTRA"}, "WAVELENGTH"),
        ({"longitud_onda": float("nan")}, "finita y positiva"),
        ({"longitud_onda": 0}, "finita y positiva"),
    ],
)
def test_estructura_invalida_controlada(
    crear_fits,
    tmp_path,
    monkeypatch,
    opciones,
    mensaje,
):
    archivo = crear_fits(**opciones)

    # Comprobar que el servicio explica el problema.
    with pytest.raises(ValueError, match=mensaje):
        generar_figura_m101(
            archivo,
            tmp_path / "invalida.png",
            canal=63,
        )

    # Comprobar que el endpoint transforma el error en HTTP 503.
    monkeypatch.setenv("M101_FITS_PATH", str(archivo))

    with TestClient(app) as client:
        response = client.get(ENDPOINT)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "No fue posible generar la visualización científica de M101"
    )
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize("canal", [0, -1, 64, 1.5, True])
def test_canal_invalido(crear_fits, tmp_path, canal):
    archivo = crear_fits()

    with pytest.raises(ValueError):
        generar_figura_m101(
            archivo,
            tmp_path / "canal_invalido.png",
            canal=canal,
        )


def test_m101_preview_without_configuration(monkeypatch):
    monkeypatch.delenv("M101_FITS_PATH", raising=False)

    with TestClient(app) as client:
        response = client.get(ENDPOINT)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El archivo científico de M101 no está configurado"
    )


def test_m101_preview_unavailable(tmp_path, monkeypatch):
    archivo = tmp_path / "inexistente.fits"
    monkeypatch.setenv("M101_FITS_PATH", str(archivo))

    with TestClient(app) as client:
        response = client.get(ENDPOINT)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El archivo científico de M101 no está disponible"
    )
    assert str(tmp_path) not in response.text


def test_m101_preview_invalid_fits(tmp_path, monkeypatch):
    archivo = tmp_path / "corrupto.fits"
    archivo.write_bytes(b"contenido que no es FITS")
    monkeypatch.setenv("M101_FITS_PATH", str(archivo))

    with TestClient(app) as client:
        response = client.get(ENDPOINT)

    assert response.status_code == 503
    assert str(tmp_path) not in response.text


def test_m101_endpoint_documentado():
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200

    operacion = response.json()["paths"][ENDPOINT]["get"]

    assert "image/png" in operacion["responses"]["200"]["content"]
    assert "503" in operacion["responses"]

@pytest.mark.parametrize(
    ("flag", "esperado"),
    [
        (0, True),
        (1 << 1, False),
        (1 << 19, False),
        (1 << 21, True),
        ((1 << 1) | (1 << 19), False),
        ((1 << 1) | (1 << 21), False),
        ((1 << 19) | (1 << 21), False),
        ((1 << 1) | (1 << 19) | (1 << 21), False),
        # Documenta que esta política aplica únicamente el subconjunto elegido.
        (1 << 0, True),
    ],
)
def test_mascara_m101_flags(flag, esperado):
    imagen = np.array([[1.0]])
    hits = np.array([[1]])
    flags = np.array([[flag]], dtype=np.int32)

    resultado = crear_mascara_m101(imagen, hits, flags)

    assert resultado.dtype == np.bool_
    assert resultado.shape == imagen.shape
    assert bool(resultado[0, 0]) is esperado


@pytest.mark.parametrize("valor", [np.nan, np.inf, -np.inf])
def test_mascara_m101_excluye_imagen_no_finita(valor):
    imagen = np.array([[valor]])
    hits = np.array([[1]])
    flags = np.array([[0]], dtype=np.int32)

    resultado = crear_mascara_m101(imagen, hits, flags)

    assert not resultado[0, 0]


@pytest.mark.parametrize("cobertura", [0, -1])
def test_mascara_m101_exige_cobertura_positiva(cobertura):
    imagen = np.array([[1.0]])
    hits = np.array([[cobertura]])
    flags = np.array([[0]], dtype=np.int32)

    resultado = crear_mascara_m101(imagen, hits, flags)

    assert not resultado[0, 0]


def test_mascara_m101_conserva_flujo_negativo_finito():
    imagen = np.array([[-0.5]])
    hits = np.array([[1]])
    flags = np.array([[0]], dtype=np.int32)

    resultado = crear_mascara_m101(imagen, hits, flags)

    assert resultado[0, 0]