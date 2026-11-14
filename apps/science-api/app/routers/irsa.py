from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app.clients.irsa import (
    IrsaResponseError,
    IrsaTimeoutError,
    IrsaUnavailableError,
)
from app.schemas.irsa import Band, IrsaQuery, IrsaResponse
from app.services.irsa import search_observations


router = APIRouter(
    prefix="/api/v1/irsa",
    tags=["IRSA"],
)


@router.get(
    "/observations",
    response_model=IrsaResponse,
    summary="Consultar metadatos de observaciones SPHEREx",
    description=(
        "Busca imágenes que cubran una posición ICRS y una banda. "
        "Devuelve hasta 100 resultados ordenados por tiempo. "
        "Los enlaces apuntan a recortes de 0.025 grados; "
        "este endpoint no descarga los FITS. "
        "count indica las filas devueltas, no el total del archivo."
    ),
    responses={
        502: {"description": "Respuesta externa inválida o fallida"},
        503: {"description": "IRSA no disponible"},
        504: {"description": "Tiempo de espera agotado"},
    },
)
def get_irsa_observations(
    ra: Annotated[
        float,
        Query(ge=0, lt=360, allow_inf_nan=False,
              description="Ascensión recta ICRS en grados"),
    ],
    dec: Annotated[
        float,
        Query(ge=-90, le=90, allow_inf_nan=False,
              description="Declinación ICRS en grados"),
    ],
    band: Band = "SPHEREx-D1",
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    query = IrsaQuery(
        ra=ra,
        dec=dec,
        band=band,
        limit=limit,
    )

    try:
        return search_observations(query)

    except IrsaTimeoutError:
        raise HTTPException(
            status_code=504,
            detail="IRSA agotó el tiempo de espera",
        ) from None

    except IrsaUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="El servicio de IRSA no está disponible",
        ) from None

    except IrsaResponseError:
        raise HTTPException(
            status_code=502,
            detail="No se obtuvo una respuesta válida de IRSA",
        ) from None