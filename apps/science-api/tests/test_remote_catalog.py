import json

import pytest
from fastapi.testclient import TestClient
from app.services.objects import make_object_id

from app.main import app
from app.services import observations as observations_service
from app.services import remote_catalog as remote_catalog_service

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import httpx

from app.clients import irsa_cutouts


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    # Directorio local vacío y registro remoto temporal.
    fits_dir = tmp_path / "fits"
    fits_dir.mkdir()

    metadata_path = tmp_path / "observations.json"

    monkeypatch.setattr(
        observations_service,
        "FITS_DIR",
        fits_dir,
    )
    monkeypatch.setattr(
        remote_catalog_service,
        "M101_METADATA_PATH",
        metadata_path,
    )

    return fits_dir, metadata_path


@pytest.fixture
def registro():
    """Metadatos sintéticos para probar el contrato y la agrupación."""
    observation = {
        "observation_id": "exposure-example",
        "product_id": "ivo://example/qr2/exposure-example/D4",
        "collection": "spherex_qr2",
        "band": "SPHEREx-D4",
        "image_center_ra_deg": 210.8,
        "image_center_dec_deg": 54.3,
        "start_mjd": 60816.5,
        "end_mjd": 60816.501,
        "start_utc": "2025-05-21T12:00:00.000Z",
        "access_url": "https://example.org/image.fits",
        "access_format": "image/fits",
    }

    return {
        "schema_version": 1,
        "queried_at_utc": "2026-11-12T00:00:00Z",
        "target": {
            "name": "M101",
            "position_source": "Posición de ejemplo para pruebas",
            "reference_product_url": "https://example.org/m101.fits",
        },
        "association": {
            "type": "spatial_intersection",
            "description": "Intersección espacial de prueba",
        },
        "result": {
            "source": "IRSA SIA",
            "collection": "spherex_qr2",
            "query": {
                "collection": "spherex_qr2",
                "ra": 210.8022671,
                "dec": 54.34895,
                "radius_arcsec": 30,
                "band": "SPHEREx-D4",
                "limit": 2,
            },
            "count": 1,
            "observations": [observation],
        },
    }


def guardar(path, registro):
    path.write_text(
        json.dumps(registro),
        encoding="utf-8",
    )


def test_registro_ausente(entorno):
    assert remote_catalog_service.load_m101_snapshot() is None

    with TestClient(app) as client:
        response = client.get("/api/v1/objects")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "objects": []}


def test_registro_valido(entorno, registro):
    _, path = entorno
    guardar(path, registro)

    snapshot = remote_catalog_service.load_m101_snapshot()

    assert snapshot.target.name == "M101"
    assert snapshot.result.count == 1
    assert snapshot.result.observations[0].product_id == (
        registro["result"]["observations"][0]["product_id"]
    )


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/objects",
        f"/api/v1/objects/{make_object_id('M101')}",
    ],
)
@pytest.mark.parametrize(
    "contenido",
    [
        "{JSON incompleto",
        "{}",
        '{"schema_version": 99}',
    ],
)
def test_registro_invalido(entorno, contenido, url):
    _, path = entorno
    path.write_text(contenido, encoding="utf-8")

    with pytest.raises(ValueError, match="estructura inválida"):
        remote_catalog_service.load_m101_snapshot()

    with TestClient(app) as client:
        response = client.get(url)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El registro remoto de observaciones no está disponible o es inválido"
    )
    assert str(path) not in response.text


def test_productos_duplicados_rechazados(entorno, registro):
    _, path = entorno

    observations = registro["result"]["observations"]
    observations.append(dict(observations[0]))
    registro["result"]["count"] = 2

    guardar(path, registro)

    with pytest.raises(ValueError, match="estructura inválida"):
        remote_catalog_service.load_m101_snapshot()


def test_registro_vacio_no_crea_objeto(entorno, registro):
    _, path = entorno
    registro["result"]["observations"] = []
    registro["result"]["count"] = 0
    guardar(path, registro)

    with TestClient(app) as client:
        response = client.get("/api/v1/objects")

    assert response.status_code == 200
    assert response.json() == {"total": 0, "objects": []}


@pytest.mark.parametrize("nombre_local", [None, "M101", "m101"])
def test_integracion_remota_sin_duplicar_objeto(
    entorno,
    registro,
    nombre_local,
):
    fits_dir, path = entorno
    guardar(path, registro)

    if nombre_local is not None:
        # El catálogo local enumera nombres de archivo.
        # Esta prueba no procesa los píxeles del FITS.
        (fits_dir / f"{nombre_local}_D1_test.fits").touch()

    with TestClient(app) as client:
        response = client.get("/api/v1/objects", params={"q": "m101"})

        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 1
        assert len(data["objects"]) == 1

        summary = data["objects"][0]
        local_count = 0 if nombre_local is None else 1

        assert summary["local_observation_count"] == local_count
        assert summary["remote_observation_count"] == 1
        assert summary["observation_count"] == local_count + 1

        detail = client.get(f"/api/v1/objects/{summary['id']}")

    assert detail.status_code == 200

    target = detail.json()

    assert len(target["observations"]) == local_count
    assert len(target["remote_observations"]) == 1
    assert target["remote_association"]["type"] == "spatial_intersection"
    assert target["remote_query"]["collection"] == "spherex_qr2"
    assert target["science_preview"]["title"] == "M101 — Canal 63"

def test_preview_rechaza_url_no_permitida(entorno, registro):
    _, path = entorno

    # El registro de prueba contiene una URL de example.org.
    # El cliente de recortes debe rechazarla antes de conectarse.
    guardar(path, registro)

    product_id = registro["result"]["observations"][0]["product_id"]
    object_id = make_object_id("M101")

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/objects/{object_id}/remote-preview",
            params={"product_id": product_id},
        )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "No fue posible obtener una previsualización válida de IRSA"
    )
    assert str(path) not in response.text


def test_preview_registro_invalido_devuelve_503(entorno):
    _, path = entorno
    path.write_text("{JSON incompleto", encoding="utf-8")

    object_id = make_object_id("M101")

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/objects/{object_id}/remote-preview",
            params={"product_id": "ivo://example/product"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El catálogo de observaciones no está disponible"
    )
    assert str(path) not in response.text

def test_preview_timeout_devuelve_504(
    entorno,
    registro,
    monkeypatch,
):
    _, metadata_path = entorno
    requests_received = []

    class SlowHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            requests_received.append(self.path)

            self.send_response(200)
            self.send_header("Content-Type", "application/fits")
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.flush()

            # El cliente debe agotar su espera de lectura.
            Event().wait(0.5)
            self.close_connection = True

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        SlowHandler,
    )
    server.daemon_threads = True

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    origin = f"http://{host}:{port}"

    try:
        # Configuración exclusiva de esta prueba.
        monkeypatch.setattr(
            irsa_cutouts,
            "IRSA_CUTOUT_ORIGIN",
            origin,
        )
        monkeypatch.setattr(
            irsa_cutouts,
            "CUTOUT_TIMEOUT",
            httpx.Timeout(
                connect=2.0,
                read=0.1,
                write=2.0,
                pool=2.0,
            ),
        )

        observation = registro["result"]["observations"][0]
        observation["access_url"] = (
            f"{origin}/ibe/data/spherex/test.fits"
        )

        guardar(metadata_path, registro)

        object_id = make_object_id("M101")

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/objects/{object_id}/remote-preview",
                params={
                    "product_id": observation["product_id"],
                },
            )

        assert response.status_code == 504
        assert response.json()["detail"] == (
            "Se agotó el tiempo de espera al descargar el recorte"
        )
        assert len(requests_received) == 1
        assert str(metadata_path) not in response.text

    finally:
        server.shutdown()
        server.server_close()
        thread.join()

def test_catalogo_local_funciona_sin_registro_remoto(entorno):
    fits_dir, _ = entorno

    # El catálogo enumera el nombre; esta prueba no procesa sus píxeles.
    (fits_dir / "SIMP_D1_test.fits").touch()

    with TestClient(app) as client:
        response = client.get("/api/v1/objects")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["objects"][0]["name"] == "SIMP"
    assert data["objects"][0]["local_observation_count"] == 1
    assert data["objects"][0]["remote_observation_count"] == 0


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/objects",
        f"/api/v1/objects/{make_object_id('M101')}",
    ],
)
def test_directorio_local_obligatorio_con_registro_remoto_valido(
    entorno,
    registro,
    monkeypatch,
    url,
):
    fits_dir, metadata_path = entorno
    guardar(metadata_path, registro)

    monkeypatch.setattr(
        observations_service,
        "FITS_DIR",
        fits_dir / "directorio_inexistente",
    )

    with TestClient(app) as client:
        response = client.get(url)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El catálogo local de observaciones no está disponible"
    )
    assert str(fits_dir) not in response.text


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/objects?q=SIMP",
        f"/api/v1/objects/{make_object_id('SIMP')}",
    ],
)
def test_registro_remoto_invalido_bloquea_catalogo_local(
    entorno,
    url,
):
    fits_dir, metadata_path = entorno

    (fits_dir / "SIMP_D1_test.fits").touch()
    metadata_path.write_text("{JSON incompleto", encoding="utf-8")

    with TestClient(app) as client:
        response = client.get(url)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El registro remoto de observaciones no está disponible o es inválido"
    )
    assert str(metadata_path) not in response.text

@pytest.mark.parametrize(
    "scenario",
    ["utf8_invalido", "directorio"],
)
@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/objects",
        f"/api/v1/objects/{make_object_id('M101')}",
    ],
)
def test_errores_de_lectura_del_registro_remoto(
    entorno,
    scenario,
    url,
):
    """Los errores de lectura deben controlarse sin exponer rutas."""
    _, path = entorno

    if scenario == "utf8_invalido":
        path.write_bytes(b"\xff\xfe\xfa")
    else:
        path.mkdir()

    # El servicio comunica un error propio, independiente de FastAPI.
    with pytest.raises(
        remote_catalog_service.RemoteCatalogError,
        match="No fue posible leer",
    ):
        remote_catalog_service.load_m101_snapshot()

    # El router convierte ese error en una respuesta HTTP controlada.
    with TestClient(app) as client:
        response = client.get(url)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El registro remoto de observaciones no está disponible o es inválido"
    )
    assert str(path) not in response.text

@pytest.mark.parametrize(
    "scenario",
    [
        "coleccion_respuesta",
        "coleccion_observacion",
        "banda_observacion",
        "coleccion_respuesta_vacia",
    ],
)
def test_registro_remoto_rechaza_incoherencias_sia(
    entorno,
    registro,
    scenario,
):
    """El registro debe conservar las validaciones de SiaResponse."""
    _, path = entorno
    result = registro["result"]

    if scenario == "coleccion_respuesta":
        result["collection"] = "spherex_qr3"

    elif scenario == "coleccion_observacion":
        result["observations"][0]["collection"] = "spherex_qr3"

    elif scenario == "banda_observacion":
        result["observations"][0]["band"] = "SPHEREx-D2"

    else:
        result["observations"] = []
        result["count"] = 0
        result["collection"] = "spherex_qr3"

    guardar(path, registro)

    with pytest.raises(
        remote_catalog_service.RemoteCatalogError,
        match="estructura inválida",
    ):

        remote_catalog_service.load_m101_snapshot()

def test_preview_url_malformada_invalida_el_registro(
    entorno,
    registro,
):
    """Pydantic rechaza la URL antes de intentar una descarga."""
    _, path = entorno

    malformed_url = (
        "https://[irsa.ipac.caltech.edu/"
        "ibe/data/spherex/test.fits"
    )

    observation = registro["result"]["observations"][0]
    observation["access_url"] = malformed_url

    guardar(path, registro)

    object_id = make_object_id("M101")

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/objects/{object_id}/remote-preview",
            params={"product_id": observation["product_id"]},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "El catálogo de observaciones no está disponible"
    )
    assert str(path) not in response.text
    assert malformed_url not in response.text