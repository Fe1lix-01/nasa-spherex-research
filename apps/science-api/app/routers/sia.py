import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.clients.irsa import (
    IrsaResponseError,
    IrsaTimeoutError,
    IrsaUnavailableError,
)
from app.schemas.sia import SiaQuery, SiaResponse
from app.services.sia import list_sia_observations

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/v1/sia",
    tags=["SIA"],
)


@router.get(
    "/observations",
    response_model=SiaResponse,
    summary="Consultar imágenes SPHEREx mediante IRSA SIA",
    description=(
        "Busca imágenes de la colección seleccionada que intersecten"
        "un círculo ICRS. Filtra por detector y devuelve las primeras "
        "observaciones ordenadas por fecha. El límite se aplica "
        "después de consultar IRSA. count representa las observaciones "
        "devueltas. access_url enlaza al producto original de IRSA."
    ),
    responses={
        502: {
            "description": "Respuesta externa fallida, inválida o incompleta",
        },
        503: {
            "description": "IRSA no disponible",
        },
        504: {
            "description": "Tiempo de espera agotado",
        },
    },
)
def get_sia_observations(
    query: Annotated[SiaQuery, Query()],
) -> SiaResponse:
    try:
        return list_sia_observations(query)

    except IrsaTimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Se agotó el tiempo de espera al consultar IRSA SIA",
        ) from None

    except IrsaUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="IRSA SIA no está disponible en este momento",
        ) from None

    except IrsaResponseError:
        logger.exception("Error al consultar o transformar IRSA SIA")
        
        raise HTTPException(
            status_code=502,
            detail="IRSA SIA devolvió una respuesta inválida o incompleta",
        ) from None

    