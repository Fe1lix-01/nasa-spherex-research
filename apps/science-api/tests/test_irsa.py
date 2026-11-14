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

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from urllib.parse import parse_qs, urlsplit

import httpx

from app.clients import irsa as irsa_client
from app.clients.irsa import (
    IrsaClient,
    IrsaTimeoutError,
    IrsaUnavailableError,
)


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

@pytest.fixture
def backend_tap_local(monkeypatch):
    """Servidor HTTP controlado para probar el cliente TAP."""
    state = {
        "statuses": [200],
        "content": HEADER.encode("utf-8"),
        "delay": 0,
        "requests": [],
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            index = len(state["requests"])
            state["requests"].append(
                parse_qs(urlsplit(self.path).query)
            )

            statuses = state["statuses"]
            status = statuses[min(index, len(statuses) - 1)]
            content = state["content"]

            self.send_response(status)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.flush()

            Event().wait(state["delay"])

            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address

    monkeypatch.setattr(
        irsa_client,
        "IRSA_TAP_URL",
        f"http://{host}:{port}/TAP/sync",
    )

    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_tap_http_success(backend_tap_local, query):
    result = IrsaClient().fetch_observations_csv(query)

    assert result == HEADER
    assert len(backend_tap_local["requests"]) == 1

    request = backend_tap_local["requests"][0]

    assert request["REQUEST"] == ["doQuery"]
    assert request["LANG"] == ["ADQL"]
    assert request["FORMAT"] == ["csv"]
    assert request["QUERY"] == [build_query(query)]


@pytest.mark.parametrize("status", [400, 404])
def test_tap_does_not_retry_permanent_error(
    backend_tap_local,
    query,
    status,
):
    backend_tap_local["statuses"] = [status]

    with pytest.raises(IrsaResponseError):
        IrsaClient().fetch_observations_csv(query)

    assert len(backend_tap_local["requests"]) == 1


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_tap_limits_transient_retries(
    backend_tap_local,
    query,
    status,
):
    backend_tap_local["statuses"] = [status]

    with pytest.raises(IrsaUnavailableError):
        IrsaClient().fetch_observations_csv(query)

    assert len(backend_tap_local["requests"]) == 3


def test_tap_recovers_after_transient_error(
    backend_tap_local,
    query,
):
    backend_tap_local["statuses"] = [503, 200]

    result = IrsaClient().fetch_observations_csv(query)

    assert result == HEADER
    assert len(backend_tap_local["requests"]) == 2


def test_tap_read_timeout(
    backend_tap_local,
    query,
):
    backend_tap_local["delay"] = 0.5

    timeout = httpx.Timeout(
        connect=2.0,
        read=0.1,
        write=2.0,
        pool=2.0,
    )

    with pytest.raises(IrsaTimeoutError):
        IrsaClient(timeout=timeout).fetch_observations_csv(query)

    assert len(backend_tap_local["requests"]) == 3