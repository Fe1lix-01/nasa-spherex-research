import time

import httpx

from app.schemas.irsa import IrsaQuery


IRSA_TAP_URL = "https://irsa.ipac.caltech.edu/TAP/sync"
CUTOUT_SIZE_DEG = 0.025

# Tres intentos en total: uno inicial y hasta dos reintentos.
MAX_ATTEMPTS = 3

# Solo estos estados HTTP se consideran transitorios aquí.
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


class IrsaError(Exception):
    """Error base de la integración."""


class IrsaTimeoutError(IrsaError):
    """El servicio externo agotó el tiempo de espera."""


class IrsaUnavailableError(IrsaError):
    """No se pudo establecer o mantener la comunicación."""


class IrsaResponseError(IrsaError):
    """Respuesta HTTP fallida o contenido externo inválido."""


def build_query(query: IrsaQuery) -> str:
    """Construye la consulta demostrada en la práctica 6."""

    # Los números y la banda ya fueron validados por Pydantic.
    return f"""
    SELECT TOP {query.limit}
        p.time_bounds_lower,
        p.time_bounds_upper,
        p.energy_bandpassname,
        'https://irsa.ipac.caltech.edu/' || a.uri
        || '?center={query.ra},{query.dec}d&size={CUTOUT_SIZE_DEG}'
        AS cutout_url
    FROM spherex.artifact a
    JOIN spherex.plane p ON a.planeid = p.planeid
    WHERE 1 = CONTAINS(
        POINT('ICRS', {query.ra}, {query.dec}),
        p.poly
    )
    AND p.energy_bandpassname = '{query.band}'
    ORDER BY p.time_bounds_lower
    """


class IrsaClient:
    """Cliente reutilizable para una consulta de metadatos."""

    def fetch_observations_csv(self, query: IrsaQuery) -> str:
        # Se configura explícitamente cada tipo de timeout.
        timeout = httpx.Timeout(
            connect=10.0,
            read=60.0,
            write=10.0,
            pool=10.0,
        )

        params = {
            "REQUEST": "doQuery",
            "LANG": "ADQL",
            "FORMAT": "csv",
            "QUERY": build_query(query),
        }

        # Crear o importar esta clase no consulta IRSA.
        # La solicitud ocurre únicamente al llamar al método.
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            for attempt in range(MAX_ATTEMPTS):
                try:
                    response = client.get(
                        IRSA_TAP_URL,
                        params=params,
                    )

                except httpx.TimeoutException:
                    if attempt == MAX_ATTEMPTS - 1:
                        raise IrsaTimeoutError() from None

                except (
                    httpx.NetworkError,
                    httpx.RemoteProtocolError,
                ):
                    if attempt == MAX_ATTEMPTS - 1:
                        raise IrsaUnavailableError() from None

                except httpx.RequestError:
                    # Otros errores de solicitud no se reintentan.
                    raise IrsaUnavailableError() from None

                else:
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt == MAX_ATTEMPTS - 1:
                            raise IrsaUnavailableError()

                    elif not response.is_success:
                        # Por ejemplo, 400 o 404 no se reintentan.
                        raise IrsaResponseError()

                    else:
                        return response.text

                # Esperas de 1 y 2 segundos antes de reintentar.
                # Nunca se duerme después del último intento.
                time.sleep(attempt + 1)

        raise IrsaUnavailableError()