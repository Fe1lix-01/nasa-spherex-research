from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import httpx
import pytest

from app.clients.irsa import (
    IrsaResponseError,
    IrsaTimeoutError,
    IrsaUnavailableError,
)
from app.clients.irsa_cutouts import (
    _fetch_cutout,
    download_irsa_cutout,
)


class CutoutHandler(BaseHTTPRequestHandler):
    """Servidor HTTP de prueba con respuestas controladas."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/slow":
            self.send_response(200)
            self.send_header("Content-Length", "10")
            self.end_headers()
            self.wfile.flush()

            # El cliente agotará su espera antes de recibir el cuerpo.
            Event().wait(0.5)
            self.close_connection = True
            return

        if self.path == "/truncated":
            self.send_response(200)
            self.send_header("Content-Length", "100")
            self.end_headers()
            self.wfile.write(b"short")
            self.wfile.flush()
            self.close_connection = True
            return

        responses = {
            "/ok": (200, b"example-content"),
            "/error": (503, b"external-error"),
            "/empty": (200, b""),
            "/large": (200, b"x" * 1024),
            "/redirect": (302, b""),
        }

        status, content = responses[self.path]

        self.send_response(status)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


@pytest.fixture
def servidor():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        CutoutHandler,
    )
    server.daemon_threads = True

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address

    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def descargar(url, *, max_bytes=4096, read_timeout=2.0):
    return _fetch_cutout(
        url=url,
        params={},
        timeout=httpx.Timeout(
            connect=2.0,
            read=read_timeout,
            write=2.0,
            pool=2.0,
        ),
        max_bytes=max_bytes,
    )


def test_descarga_correcta(servidor):
    assert descargar(f"{servidor}/ok") == b"example-content"


@pytest.mark.parametrize("path", ["/error", "/empty", "/redirect"])
def test_rechaza_respuesta_fallida_o_vacia(servidor, path):
    with pytest.raises(IrsaResponseError):
        descargar(f"{servidor}{path}")


def test_limite_de_tamano(servidor):
    with pytest.raises(IrsaResponseError, match="tamaño permitido"):
        descargar(f"{servidor}/large", max_bytes=100)


def test_descarga_incompleta(servidor):
    with pytest.raises(IrsaUnavailableError):
        descargar(f"{servidor}/truncated")


def test_timeout_durante_descarga(servidor):
    with pytest.raises(IrsaTimeoutError):
        descargar(
            f"{servidor}/slow",
            read_timeout=0.1,
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://irsa.ipac.caltech.edu/ibe/data/spherex/test.fits",
        "https://example.org/ibe/data/spherex/test.fits",
        "https://irsa.ipac.caltech.edu/otro/test.fits",
        "https://irsa.ipac.caltech.edu/ibe/data/spherex/test.txt",
        "https://irsa.ipac.caltech.edu/ibe/data/spherex/test.fits?x=1",
        "https://irsa.ipac.caltech.edu/ibe/data/spherex/test.fits#fragment",
    ],
)
def test_rechaza_url_no_permitida(url):
    with pytest.raises(IrsaResponseError, match="URL del producto"):
        download_irsa_cutout(url, ra=210.8, dec=54.3)