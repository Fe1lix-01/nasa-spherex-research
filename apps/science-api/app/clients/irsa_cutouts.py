from urllib.parse import urlsplit

import httpx

from app.clients.irsa import (
    CUTOUT_SIZE_DEG,
    IrsaResponseError,
    IrsaTimeoutError,
    IrsaUnavailableError,
)


MAX_CUTOUT_BYTES = 8 * 1024 * 1024

IRSA_CUTOUT_ORIGIN = "https://irsa.ipac.caltech.edu"

CUTOUT_TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=60.0,
    write=10.0,
    pool=10.0,
)


def _fetch_cutout(
    url: str,
    params: dict[str, str],
    timeout: httpx.Timeout,
    max_bytes: int,
) -> bytes:
    """Ejecuta y controla la descarga de un recorte."""
    transport = httpx.HTTPTransport(retries=2)

    try:
        with httpx.Client(
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
        ) as client:
            with client.stream("GET", url, params=params) as response:
                if not response.is_success:
                    raise IrsaResponseError(
                        "IRSA rechazó la solicitud del recorte."
                    )

                content = bytearray()

                for chunk in response.iter_bytes():
                    content.extend(chunk)

                    if len(content) > max_bytes:
                        raise IrsaResponseError(
                            "El recorte supera el tamaño permitido."
                        )

                if not content:
                    raise IrsaResponseError(
                        "IRSA devolvió un recorte vacío."
                    )

                return bytes(content)

    except httpx.TimeoutException:
        raise IrsaTimeoutError() from None

    except httpx.RequestError:
        raise IrsaUnavailableError() from None


def download_irsa_cutout(url: str, ra: float, dec: float) -> bytes:
    """Valida el producto registrado y solicita su recorte a IRSA."""
    parsed = urlsplit(url)
    allowed_origin = urlsplit(IRSA_CUTOUT_ORIGIN)

    if (
        parsed.scheme != allowed_origin.scheme
        or parsed.netloc != allowed_origin.netloc
        or not parsed.path.startswith("/ibe/data/spherex/")
        or not parsed.path.endswith(".fits")
        or parsed.query
        or parsed.fragment
    ):
        raise IrsaResponseError(
            "La URL del producto IRSA no es válida."
        )

    return _fetch_cutout(
        url=url,
        params={
            "center": f"{ra},{dec}d",
            "size": str(CUTOUT_SIZE_DEG),
        },
        timeout=CUTOUT_TIMEOUT,
        max_bytes=MAX_CUTOUT_BYTES,
    )