import httpx
import pytest

import app.clients.irsa as irsa_module

from app.clients.irsa import (
    IrsaClient,
    IrsaResponseError,
    IrsaTimeoutError,
    IrsaUnavailableError,
)
from app.schemas.irsa import IrsaQuery


@pytest.fixture
def query():
    return IrsaQuery(ra=24.24, dec=9.56)


class FakeClient:
    """Cliente HTTP simulado para probar sin conexiones externas."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, *args, **kwargs):
        self.calls += 1
        result = self.responses.pop(0)

        if isinstance(result, Exception):
            raise result

        return result


def response(status_code, text="resultado,csv"):
    """Construye una respuesta HTTP simulada."""
    return httpx.Response(
        status_code=status_code,
        text=text,
        request=httpx.Request("GET", irsa_module.IRSA_TAP_URL),
    )


def install_fake_client(monkeypatch, fake):
    """Sustituye el cliente HTTP real por el simulado."""
    monkeypatch.setattr(
        irsa_module.httpx,
        "Client",
        lambda **kwargs: fake,
    )
    monkeypatch.setattr(irsa_module.time, "sleep", lambda seconds: None)


def test_respuesta_exitosa(monkeypatch, query):
    fake = FakeClient([response(200, "time_bounds_lower\n60868")])
    install_fake_client(monkeypatch, fake)

    result = IrsaClient().fetch_observations_csv(query)

    assert result == "time_bounds_lower\n60868"
    assert fake.calls == 1


@pytest.mark.parametrize("status_code", [429, 502, 503, 504])
def test_reintenta_estados_transitorios(monkeypatch, query, status_code):
    fake = FakeClient([
        response(status_code),
        response(200, "resultado correcto"),
    ])
    install_fake_client(monkeypatch, fake)

    result = IrsaClient().fetch_observations_csv(query)

    assert result == "resultado correcto"
    assert fake.calls == 2


def test_error_http_no_transitorio_no_se_reintenta(monkeypatch, query):
    fake = FakeClient([response(400)])
    install_fake_client(monkeypatch, fake)

    with pytest.raises(IrsaResponseError):
        IrsaClient().fetch_observations_csv(query)

    assert fake.calls == 1


def test_timeout_agota_tres_intentos(monkeypatch, query):
    fake = FakeClient([
        httpx.ReadTimeout("timeout"),
        httpx.ReadTimeout("timeout"),
        httpx.ReadTimeout("timeout"),
    ])
    install_fake_client(monkeypatch, fake)

    with pytest.raises(IrsaTimeoutError):
        IrsaClient().fetch_observations_csv(query)

    assert fake.calls == 3


def test_error_de_conexion_agota_tres_intentos(monkeypatch, query):
    fake = FakeClient([
        httpx.ConnectError("connection failed"),
        httpx.ConnectError("connection failed"),
        httpx.ConnectError("connection failed"),
    ])
    install_fake_client(monkeypatch, fake)

    with pytest.raises(IrsaUnavailableError):
        IrsaClient().fetch_observations_csv(query)

    assert fake.calls == 3
