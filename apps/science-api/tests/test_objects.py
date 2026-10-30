# Herramientas para definir y ejecutar pruebas.
import pytest

# Permite enviar solicitudes a la aplicación
# sin iniciar Uvicorn ni abrir un navegador.
from fastapi.testclient import TestClient

from app.main import app
from app.services import observations as observations_service
from app.services.objects import list_objects

# Cliente HTTP de prueba conectado a nuestra aplicación.
client = TestClient(app)


def make_observations(name, detectors):
    """Genera metadatos de prueba; no crea archivos científicos."""
    return [
        {
            "id": f"{name}_{detector}_100_arcsec_cutout.fits",
            "detector": detector,
            "filename": f"{name}_{detector}_100_arcsec_cutout.fits",
            "format": "FITS",
        }
        for detector in detectors
    ]


@pytest.fixture
def sample_catalog(monkeypatch):
    observations = make_observations(
        "T2 SIMP J013656.5+093347.3",
        ["D1", "D2", "D3", "D4", "D5", "D6"],
    )

    monkeypatch.setattr(
        observations_service,
        "list_observations",
        lambda: observations,
    )

    return observations


def test_list_groups_six_observations(sample_catalog):
    response = client.get("/api/v1/objects")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["objects"]) == 1

    item = data["objects"][0]

    assert item["name"] == "T2 SIMP J013656.5+093347.3"
    assert item["observation_count"] == 6
    assert item["detectors"] == [
        "D1", "D2", "D3", "D4", "D5", "D6"
    ]
    assert "observations" not in item


def test_get_object_by_id(sample_catalog):
    listed = client.get("/api/v1/objects").json()
    object_id = listed["objects"][0]["id"]

    response = client.get(f"/api/v1/objects/{object_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == object_id
    assert data["observation_count"] == 6
    assert len(data["observations"]) == 6
    assert data["observations"] == sample_catalog


def test_unknown_object_returns_404(sample_catalog):
    response = client.get("/api/v1/objects/no-existe")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Objeto astronómico no encontrado"
    )


@pytest.mark.parametrize("query", ["SIMP", "simp", "j013656"])
def test_search_is_partial_and_case_insensitive(
    sample_catalog, query
):
    response = client.get(
        "/api/v1/objects",
        params={"q": query},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_search_without_matches(sample_catalog):
    response = client.get(
        "/api/v1/objects",
        params={"q": "nombre-inexistente"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "objects": [],
    }


def test_counts_objects_separately_from_observations(
    monkeypatch, sample_catalog
):
    observations = sample_catalog + make_observations(
        "Objeto de prueba B",
        ["D1", "D2"],
    )

    monkeypatch.setattr(
        observations_service,
        "list_observations",
        lambda: observations,
    )

    response = client.get("/api/v1/objects")
    data = response.json()

    assert response.status_code == 200
    assert data["total"] == 2
    assert sorted(
        item["observation_count"]
        for item in data["objects"]
    ) == [2, 6]


def test_ids_are_stable_when_order_changes(
    monkeypatch, sample_catalog
):
    first = list_objects()[0]["id"]

    monkeypatch.setattr(
        observations_service,
        "list_observations",
        lambda: list(reversed(sample_catalog)),
    )

    second = list_objects()[0]["id"]

    assert first == second


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/objects",
        "/api/v1/objects/no-existe",
    ],
)
def test_unavailable_catalog_returns_503(monkeypatch, url):
    def unavailable():
        raise FileNotFoundError("ruta-local-privada")

    monkeypatch.setattr(
        observations_service,
        "list_observations",
        unavailable,
    )

    response = client.get(url)

    assert response.status_code == 503
    assert "ruta-local-privada" not in response.text


def test_empty_catalog(monkeypatch):
    monkeypatch.setattr(
        observations_service,
        "list_observations",
        lambda: [],
    )

    response = client.get("/api/v1/objects")

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "objects": [],
    }


def test_objects_appear_in_openapi():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/objects" in paths
    assert "/api/v1/objects/{object_id}" in paths


def test_local_catalog_integration():
    """Depende de los FITS locales; se omite si no están disponibles."""
    if not observations_service.FITS_DIR.is_dir():
        pytest.skip("El directorio de FITS locales no está disponible")

    observations = observations_service.list_observations()

    if not observations:
        pytest.skip("No hay observaciones locales disponibles")

    response = client.get("/api/v1/objects")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert sum(
        item["observation_count"]
        for item in data["objects"]
    ) == len(observations)