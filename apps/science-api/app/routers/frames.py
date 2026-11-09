
"""
Rutas HTTP para consultar los frames astronómicos disponibles.

Este router expone:
- GET /api/v1/frames
"""

# APIRouter permite agrupar los endpoints de frames.
# HTTPException permite devolver errores HTTP controlados.
from fastapi import APIRouter, HTTPException

# Importamos el esquema que valida la respuesta.
from app.schemas.frames import FramesResponse

# Importamos el servicio encargado de leer los metadatos FITS.
from app.services.frames import FrameMetadataError, list_frames


# Creamos el router y definimos el prefijo común.
router = APIRouter(
    prefix="/api/v1",
    tags=["Frames"]
)


@router.get(
    "/frames",
    response_model=FramesResponse
)
def get_frames():
    """
    Devuelve los metadatos astronómicos de los FITS disponibles.

    No convierte ni modifica los archivos científicos originales.
    """

    try:
        # Obtenemos los metadatos de los frames disponibles.
        frames = list_frames()

        # Devolvemos el total y la lista de frames.
        return {
            "total": len(frames),
            "frames": frames
        }

    except FileNotFoundError:
        # Informamos que el directorio de archivos FITS no está disponible.
        raise HTTPException(
            status_code=503,
            detail="El directorio de imágenes FITS no está disponible"
        )

    except FrameMetadataError:
        # Informamos que no fue posible procesar los metadatos.
        raise HTTPException(
            status_code=503,
            detail="No fue posible procesar los metadatos astronómicos de los FITS"
        )
