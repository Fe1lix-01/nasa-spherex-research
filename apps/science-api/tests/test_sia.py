import pytest
from astropy.table import Table
from pydantic import ValidationError

from app.clients.irsa import IrsaResponseError
from app.schemas.sia import SiaQuery, SiaResponse
from app.services.sia import transform_sia_results

from io import BytesIO

from astropy.io.votable import from_table
from astropy.io.votable.tree import Info

from app.clients.sia import parse_sia_response

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.clients import sia as sia_client


def crear_tabla(collection):
    """Datos sintéticos para probar la transformación, sin consultar IRSA."""
    return Table(
        rows=[
            (
                "exposure-example",
                f"ivo://example/{collection}/exposure-example/D4",
                collection,
                "SPHEREx-D4",
                210.8,
                54.3,
                60816.5,
                60816.501,
                "https://example.org/image.fits",
                "image/fits",
            ),
        ],
        names=[
            "obs_id",
            "obs_publisher_did",
            "obs_collection",
            "energy_bandpassname",
            "s_ra",
            "s_dec",
            "t_min",
            "t_max",
            "access_url",
            "access_format",
        ],
    )


@pytest.mark.parametrize("collection", ["spherex_qr2", "spherex_qr3"])
def test_transforma_la_coleccion_solicitada(collection):
    query = SiaQuery(
        collection=collection,
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
        limit=2,
    )

    response = transform_sia_results(crear_tabla(collection), query)

    assert response.collection == collection
    assert response.query.collection == collection
    assert response.count == 1
    assert response.observations[0].collection == collection
    assert response.observations[0].product_id == (
        f"ivo://example/{collection}/exposure-example/D4"
    )


def test_rechaza_coleccion_distinta_a_la_solicitada():
    query = SiaQuery(
        collection="spherex_qr2",
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
    )

    with pytest.raises(IrsaResponseError):
        transform_sia_results(crear_tabla("spherex_qr3"), query)


def test_exige_identificador_del_producto():
    table = crear_tabla("spherex_qr2")
    table.remove_column("obs_publisher_did")

    query = SiaQuery(
        collection="spherex_qr2",
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
    )

    with pytest.raises(IrsaResponseError):
        transform_sia_results(table, query)


def test_rechaza_coleccion_no_admitida():
    with pytest.raises(ValidationError):
        SiaQuery(
            collection="coleccion-inexistente",
            ra=210.8022671,
            dec=54.34895,
        )


def test_conserva_qr3_como_valor_predeterminado():
    query = SiaQuery(ra=269.44627, dec=4.76820)

    assert query.collection == "spherex_qr3"

def crear_votable(table, status="OK"):
    """Genera una respuesta VOTable para probar el parser."""
    votable = from_table(table)
    resource = votable.resources[0]

    resource.infos.append(
        Info(name="QUERY_STATUS", value=status)
    )

    # Reproduce el caso donde ID y nombre de columna son diferentes.
    for index, field in enumerate(resource.tables[0].fields):
        field.ID = f"field_{index}"

    output = BytesIO()
    votable.to_xml(output)

    return output.getvalue()


def test_votable_conserva_nombres_de_columnas():
    original = crear_tabla("spherex_qr2")
    content = crear_votable(original)

    table = parse_sia_response(content)

    assert table.colnames == original.colnames
    assert len(table) == 1
    assert table["obs_publisher_did"][0] == (
        original["obs_publisher_did"][0]
    )


@pytest.mark.parametrize("status", ["ERROR", "OVERFLOW"])
def test_votable_rechaza_error_o_resultado_incompleto(status):
    content = crear_votable(
        crear_tabla("spherex_qr2"),
        status=status,
    )

    with pytest.raises(IrsaResponseError):
        parse_sia_response(content)


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"<html>Error externo</html>",
    ],
)
def test_rechaza_contenido_que_no_es_votable(content):
    with pytest.raises(IrsaResponseError):
        parse_sia_response(content)


@pytest.mark.parametrize("collection", ["spherex_qr2", "spherex_qr3"])
def test_resultado_vacio(collection):
    table = crear_tabla(collection)[:0]

    query = SiaQuery(
        collection=collection,
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
    )

    response = transform_sia_results(table, query)

    assert response.collection == collection
    assert response.count == 0
    assert response.observations == []


def test_filtra_ordena_y_limita_resultados():
    original = crear_tabla("spherex_qr2")
    template = {
        column: original[column][0]
        for column in original.colnames
    }

    table = original[:0]

    # Insertamos las observaciones fuera de orden.
    for index in [3, 1, 2]:
        row = dict(template)
        row["obs_id"] = f"exposure-{index}"
        row["obs_publisher_did"] = (
            f"ivo://example/qr2/product-{index}/D4"
        )
        row["t_min"] = 60816.0 + index * 0.01
        row["t_max"] = row["t_min"] + 0.001

        table.add_row(row)

    # Este resultado es anterior, pero pertenece a otro detector.
    other_detector = dict(template)
    other_detector["obs_id"] = "other-detector"
    other_detector["obs_publisher_did"] = (
        "ivo://example/qr2/other/D2"
    )
    other_detector["energy_bandpassname"] = "SPHEREx-D2"
    other_detector["t_min"] = 60815.0
    other_detector["t_max"] = 60815.001

    table.add_row(other_detector)

    query = SiaQuery(
        collection="spherex_qr2",
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
        limit=2,
    )

    response = transform_sia_results(table, query)

    assert response.count == 2
    assert [
        observation.observation_id
        for observation in response.observations
    ] == ["exposure-1", "exposure-2"]

    assert all(
        observation.band == "SPHEREx-D4"
        for observation in response.observations
    )

@pytest.fixture
def backend_sia_local(monkeypatch):
    """Servidor HTTP real de prueba, independiente de IRSA."""
    state = {
        "statuses": [200],
        "content": crear_votable(crear_tabla("spherex_qr2")),
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
            self.send_header("Content-Type", "application/x-votable+xml")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.flush()

            Event().wait(state["delay"])

            try:
                self.wfile.write(content)
            except (BrokenPipeError, ConnectionResetError):
                # El cliente puede cerrar la conexión tras su timeout.
                pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address

    monkeypatch.setattr(
        sia_client,
        "IRSA_SIA_URL",
        f"http://{host}:{port}/SIA",
    )

    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def consultar_sia(**changes):
    params = {
        "collection": "spherex_qr2",
        "ra": 210.8022671,
        "dec": 54.34895,
        "radius_arcsec": 30,
        "band": "SPHEREx-D4",
        "limit": 2,
    }
    params.update(changes)

    with TestClient(app) as client:
        return client.get(
            "/api/v1/sia/observations",
            params=params,
        )


def test_endpoint_sia_consulta_http_real(backend_sia_local):
    response = consultar_sia()

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    assert data["collection"] == "spherex_qr2"
    assert data["count"] == 1
    assert data["observations"][0]["band"] == "SPHEREx-D4"

    request = backend_sia_local["requests"][0]

    assert request["COLLECTION"] == ["spherex_qr2"]

    position = request["POS"][0].split()

    assert position[0] == "CIRCLE"
    assert float(position[1]) == pytest.approx(210.8022671)
    assert float(position[2]) == pytest.approx(54.34895)
    assert float(position[3]) == pytest.approx(30 / 3600)


def test_endpoint_sia_error_400_no_reintenta(backend_sia_local):
    backend_sia_local["statuses"] = [400]

    response = consultar_sia()

    assert response.status_code == 502
    assert len(backend_sia_local["requests"]) == 1


def test_endpoint_sia_reintentos_limitados(backend_sia_local):
    backend_sia_local["statuses"] = [503]

    response = consultar_sia()

    assert response.status_code == 503
    assert len(backend_sia_local["requests"]) == 3


def test_endpoint_sia_recupera_error_transitorio(backend_sia_local):
    backend_sia_local["statuses"] = [503, 200]

    response = consultar_sia()

    assert response.status_code == 200
    assert len(backend_sia_local["requests"]) == 2


def test_endpoint_sia_rechaza_contenido_invalido(backend_sia_local):
    backend_sia_local["content"] = b"<html>Error externo</html>"

    response = consultar_sia()

    assert response.status_code == 502
    assert len(backend_sia_local["requests"]) == 1


def test_endpoint_sia_timeout_controlado(
    backend_sia_local,
    monkeypatch,
):
    backend_sia_local["delay"] = 0.5

    monkeypatch.setattr(
        sia_client,
        "SIA_TIMEOUT",
        httpx.Timeout(
            connect=2.0,
            read=0.1,
            write=2.0,
            pool=2.0,
        ),
    )

    response = consultar_sia()

    assert response.status_code == 504
    assert len(backend_sia_local["requests"]) == 3


@pytest.mark.parametrize(
    "changes",
    [
        {"ra": 360},
        {"radius_arcsec": 0},
        {"collection": "coleccion-inexistente"},
    ],
)
def test_endpoint_sia_valida_antes_de_consultar(
    backend_sia_local,
    changes,
):
    response = consultar_sia(**changes)

    assert response.status_code == 422
    assert backend_sia_local["requests"] == []
def crear_respuesta_sia_para_validacion():
    """Obtiene una respuesta de ejemplo sin consultar servicios externos."""
    query = SiaQuery(
        collection="spherex_qr2",
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
        limit=2,
    )

    response = transform_sia_results(
        crear_tabla("spherex_qr2"),
        query,
    )

    return response.model_dump(mode="json")


def test_modelo_sia_acepta_respuesta_coherente():
    data = crear_respuesta_sia_para_validacion()

    response = SiaResponse.model_validate(data)

    assert response.collection == response.query.collection
    assert response.count == len(response.observations)
    assert response.observations[0].band == response.query.band


def test_modelo_sia_rechaza_coleccion_de_respuesta_incoherente():
    data = crear_respuesta_sia_para_validacion()
    data["collection"] = "spherex_qr3"

    with pytest.raises(
        ValidationError,
        match="La colección de la respuesta",
    ):
        SiaResponse.model_validate(data)


def test_modelo_sia_rechaza_coleccion_de_observacion_incoherente():
    data = crear_respuesta_sia_para_validacion()
    data["observations"][0]["collection"] = "spherex_qr3"

    with pytest.raises(
        ValidationError,
        match="La colección de una observación",
    ):
        SiaResponse.model_validate(data)


def test_modelo_sia_rechaza_banda_de_observacion_incoherente():
    data = crear_respuesta_sia_para_validacion()
    data["observations"][0]["band"] = "SPHEREx-D2"

    with pytest.raises(
        ValidationError,
        match="La banda de una observación",
    ):
        SiaResponse.model_validate(data)


def test_modelo_sia_rechaza_coleccion_incoherente_sin_observaciones():
    data = crear_respuesta_sia_para_validacion()
    data["observations"] = []
    data["count"] = 0
    data["collection"] = "spherex_qr3"

    with pytest.raises(
        ValidationError,
        match="La colección de la respuesta",
    ):
        SiaResponse.model_validate(data)

@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("t_min", float("nan")),
        ("t_max", -1.0),
        ("s_ra", 360.0),
        ("s_dec", 91.0),
        ("obs_publisher_did", ""),
        ("obs_id", ""),
        ("access_url", "no-es-una-url"),
        ("access_format", ""),
    ],
)
def test_sia_controla_valores_externos_invalidos(column, value):
    """Los datos inválidos deben producir un error controlado."""
    table = crear_tabla("spherex_qr2")

    # Reemplazamos la columna para conservar el valor de prueba
    # sin que el tipo original de Astropy lo transforme o recorte.
    table.replace_column(column, [value])

    query = SiaQuery(
        collection="spherex_qr2",
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
        limit=2,
    )

    with pytest.raises(IrsaResponseError):
        transform_sia_results(table, query)