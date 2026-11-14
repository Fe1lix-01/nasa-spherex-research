import time
from io import BytesIO

import httpx
from astropy.io.votable import parse
from astropy.table import Table

from app.clients.irsa import (
    MAX_ATTEMPTS,
    RETRYABLE_STATUS_CODES,
    IrsaResponseError,
    IrsaTimeoutError,
    IrsaUnavailableError,
)
from app.schemas.sia import SiaQuery


IRSA_SIA_URL = "https://irsa.ipac.caltech.edu/SIA"



def parse_sia_response(content: bytes) -> Table:
    """Lee la respuesta VOTable y comprueba su estado."""

    try:
        votable = parse(BytesIO(content))

        # SIA puede comunicar un error dentro de un HTTP 200.
        for resource in votable.resources:
            for info in resource.infos:
                if info.name == "QUERY_STATUS":
                    if str(info.value).upper() != "OK":
                        raise IrsaResponseError(
                            f"QUERY_STATUS={info.value}. {info.content}"
)

            for table in resource.tables:
                for info in table.infos:
                    if info.name == "QUERY_STATUS":
                        if str(info.value).upper() != "OK":
                            raise IrsaResponseError(
                                f"QUERY_STATUS={info.value}. {info.content}"
)

        return votable.get_first_table().to_table(
            use_names_over_ids=True
)

    except IrsaResponseError:
        raise

    except Exception as error:
        # El parser puede lanzar distintos errores ante XML inválido.
        raise IrsaResponseError() from error


class SiaClient:
    """Cliente reutilizable para consultas espaciales IRSA SIA."""

    def fetch_observations(self, query: SiaQuery) -> Table:
        # SIA recibe el radio del círculo en grados.
        radius_deg = query.radius_arcsec / 3600

        params = {
            "POS": f"CIRCLE {query.ra} {query.dec} {radius_deg}",
            "COLLECTION": query.collection,
        }

        timeout = httpx.Timeout(
            connect=10.0,
            read=60.0,
            write=10.0,
            pool=10.0,
        )

        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            for attempt in range(MAX_ATTEMPTS):
                try:
                    response = client.get(
                        IRSA_SIA_URL,
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
                    raise IrsaUnavailableError() from None

                else:
                    if response.status_code in RETRYABLE_STATUS_CODES:
                        if attempt == MAX_ATTEMPTS - 1:
                            raise IrsaUnavailableError()

                    elif not response.is_success:
                        raise IrsaResponseError(
                            f"IRSA SIA respondió HTTP {response.status_code}"
                        )

                    else:
                        return parse_sia_response(response.content)

                # Esperas limitadas entre intentos.
                time.sleep(attempt + 1)

        raise IrsaUnavailableError()