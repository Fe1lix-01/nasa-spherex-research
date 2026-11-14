import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response

from app.clients.irsa import (
    IrsaResponseError,
    IrsaTimeoutError,
    IrsaUnavailableError,
)
from app.services.remote_previews import (
    RemotePreviewNotFoundError,
    render_remote_observation_png,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/objects",
    tags=["Remote previews"],
)


@router.get(
    "/{object_id}/remote-preview",
    response_class=Response,
    summary="Generar la previsualización de una imagen remota registrada",
    description=(
        "Busca el producto dentro del objeto del catálogo, descarga "
        "un recorte FITS de 0,025 grados centrado en la posición de "
        "la consulta registrada y genera un PNG. Utiliza el contraste "
        "de visualización existente, sin aplicar una máscara de FLAGS."
    ),
    responses={
        200: {
            "description": "Previsualización PNG del recorte",
            "content": {
                "image/png": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    }
                }
            },
        },
        404: {"description": "Objeto o producto no registrado"},
        502: {"description": "Respuesta o recorte de IRSA inválido"},
        503: {"description": "Catálogo o servicio externo no disponible"},
        504: {"description": "Tiempo de espera agotado"},
    },
)
def get_remote_preview(
    object_id: str,
    product_id: Annotated[
        str,
        Query(
            min_length=1,
            description="Identificador completo product_id registrado",
        ),
    ],
) -> Response:
    try:
        content = render_remote_observation_png(
            object_id=object_id,
            product_id=product_id,
        )

    except RemotePreviewNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="El objeto o producto remoto no está registrado",
        ) from None

    except IrsaTimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Se agotó el tiempo de espera al descargar el recorte",
        ) from None

    except IrsaUnavailableError:
        raise HTTPException(
            status_code=503,
            detail="No fue posible conectar con IRSA",
        ) from None

    except IrsaResponseError:
        logger.exception("Error al generar la previsualización remota")

        raise HTTPException(
            status_code=502,
            detail="No fue posible obtener una previsualización válida de IRSA",
        ) from None

    except (OSError, ValueError):
        logger.exception("Error al consultar el catálogo para la vista remota")

        raise HTTPException(
            status_code=503,
            detail="El catálogo de observaciones no está disponible",
        ) from None

    return Response(
        content=content,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )