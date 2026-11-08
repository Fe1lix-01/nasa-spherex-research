import csv
import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.clients.irsa import IrsaResponseError, build_query
from app.main import app
from app.schemas.irsa import IrsaQuery, IrsaResponse
from app.services.irsa import normalize_observations


HEADER = (
    "time_bounds_lower,time_bounds_upper,"
    "energy_bandpassname,cutout_url\n"
)


@pytest.fixture
def query():
    return IrsaQuery(
        ra=24.2412498,
        dec=9.5630705,
        band="SPHEREx-D1",
        limit=10,
    )


@pytest.fixture
def example_csv():
    # Lee una fila de la evidencia real de la práctica 6.
    # No abre una conexión ni reemplaza funciones.
    root = Path(__file__).resolve().parents[3]
    path = root / "experiments/outputs/observaciones_irsa.csv"

    with path.open(encoding="utf-8-sig", newline="") as file:
        row = next(csv.DictReader(file))

    output = io.StringIO()
    fields = [
        "time_bounds_lower",
        "time_bounds_upper",
        "energy_bandpassname",
        "cutout_url",
    ]

    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerow({field: row[field] for field in fields})

    return output.getvalue()


def test_transform_real_example(example_csv, query):
    result = normalize_observations(example_csv, query)

    assert result.source == "IRSA"
    assert result.count == 1

    item = result.observations[0]

    assert item.start_mjd == pytest.approx(60868.261990)
    assert item.end_mjd >= item.start_mjd
    assert item.band == "SPHEREx-D1"
    assert item.start_utc == "2025-07-12T06:17:15.936Z"

    # Verifica que también pueda validarse el JSON final.
    validated = IrsaResponse.model_validate_json(
        result.model_dump_json()
    )
    assert validated.count == 1


def test_empty_result(query):
    result = normalize_observations(HEADER, query)

    assert result.count == 0
    assert result.observations == []


@pytest.mark.parametrize(
    "text",
    [
        "",
        "<html>Error del servidor</html>",
        "columna_incorrecta\nvalor\n",
    ],
)
def test_invalid_response(text, query):
    with pytest.raises(IrsaResponseError):
        normalize_observations(text, query)


@pytest.mark.parametrize(
    "field,value",
    [
        ("time_bounds_lower", "no-es-un-numero"),
        ("time_bounds_lower", "nan"),
        ("time_bounds_upper", "1"),
        ("energy_bandpassname", "SPHEREx-D2"),
        ("cutout_url", "no-es-una-url"),
    ],
)
def test_invalid_row(example_csv, query, field, value):
    reader = csv.DictReader(io.StringIO(example_csv))
    row = next(reader)
    row[field] = value

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=reader.fieldnames,
    )
    writer.writeheader()
    writer.writerow(row)

    with pytest.raises(IrsaResponseError):
        normalize_observations(output.getvalue(), query)


@pytest.mark.parametrize(
    "changes",
    [
        {"ra": 360},
        {"ra": float("nan")},
        {"dec": -91},
        {"band": "SPHEREx-D9"},
        {"limit": 0},
        {"limit": 101},
    ],
)
def test_query_validation(changes, query):
    data = query.model_dump()
    data.update(changes)

    with pytest.raises(ValidationError):
        IrsaQuery.model_validate(data)


def test_response_count_validation(query):
    with pytest.raises(ValidationError):
        IrsaResponse(
            query=query,
            count=1,
            observations=[],
        )


def test_query_contains_demonstrated_filters(query):
    text = build_query(query)

    assert "SELECT TOP 10" in text
    assert "spherex.artifact" in text
    assert "spherex.plane" in text
    assert "SPHEREx-D1" in text


def test_endpoint_is_documented():
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/irsa/observations" in response.json()["paths"]


def test_invalid_parameters_return_422():
    # Los parámetros inválidos se rechazan antes de llamar a IRSA.
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/irsa/observations",
            params={"ra": 400, "dec": 0},
        )

    assert response.status_code == 422