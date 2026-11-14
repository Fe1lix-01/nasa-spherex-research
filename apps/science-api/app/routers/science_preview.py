import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock

from fastapi import APIRouter, HTTPException, Response

from app.services.m101 import generar_figura_m101


router = APIRouter(prefix="/api/v1/science", tags=["Science"])
logger = logging.getLogger(__name__)

# Matplotlib necesita que sus operaciones se ejecuten de forma secuencial.
render_lock = Lock()


@router.get(
    "/m101/channel-63/preview",
    response_class=Response,
    responses={
        200: {
            "description": "Figura del canal 63 generada desde el FITS de M101",
            "content": {
                "image/png": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    }
                }
            },
        },
        503: {
            "description": "FITS no disponible o procesamiento fallido",
        },
    },
)
def m101_channel_preview() -> Response:
    """Genera la imagen, la cobertura y la máscara del canal 63 de M101."""

    fits_path = os.environ.get("M101_FITS_PATH")

    if not fits_path:
        raise HTTPException(
            status_code=503,
            detail="El archivo científico de M101 no está configurado",
        )

    archivo = Path(fits_path)

    try:
        if not archivo.is_file():
            raise HTTPException(
                status_code=503,
                detail="El archivo científico de M101 no está disponible",
            )

        # Cada solicitud utiliza su propia carpeta temporal.
        with TemporaryDirectory(prefix="m101-") as carpeta:
            ruta_salida = Path(carpeta) / "canal_63.png"

            with render_lock:
                generar_figura_m101(
                    archivo=archivo,
                    ruta_salida=ruta_salida,
                    canal=63,
                )

            # Leemos el PNG antes de eliminar la carpeta temporal.
            contenido = ruta_salida.read_bytes()

    except (OSError, ValueError, KeyError, IndexError, TypeError):
        logger.exception("Error al generar la figura científica de M101")

        raise HTTPException(
            status_code=503,
            detail="No fue posible generar la visualización científica de M101",
        ) from None

    return Response(
        content=contenido,
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )