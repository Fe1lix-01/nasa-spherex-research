
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
# Response permite devolver contenido binario en lugar de JSON.
from fastapi.responses import Response

# Importamos el servicio de conversión y sus errores controlados.
from app.services.frame_images import (
    FrameImageError,
    FrameImageNotFoundError,
    render_frame_png,
)

# Creamos el router y definimos el prefijo común.
router = APIRouter(
    prefix="/api/v1",
    tags=["Frames"]
)



@router.get(
    "/frames/{frame_id}/image",
    response_class=Response,
    responses={
        200: {
            "description": "Imagen PNG del frame astronómico",
            "content": {
                "image/png": {
                    "schema": {
                        "type": "string",
                        "format": "binary",
                    }
                }
            },
        },
        404: {
            "description": "Frame no encontrado",
        },
        503: {
            "description": "No fue posible generar la imagen",
        },
    },
)
def get_frame_image(frame_id: str) -> Response:
    """
    Devuelve la representación PNG de un frame FITS.

    El archivo científico original permanece intacto.
    """

    try:
        # Generamos la imagen PNG utilizando el servicio correspondiente.
        png_data = render_frame_png(frame_id)

        # Devolvemos los bytes con el tipo MIME correspondiente.
        return Response(
            content=png_data,
            media_type="image/png",
        )

    except FrameImageNotFoundError:
        # El frame solicitado no existe en el directorio autorizado.
        raise HTTPException(
            status_code=404,
            detail="No existe el frame solicitado",
        )

    except FileNotFoundError:
        # El directorio de archivos científicos no está disponible.
        raise HTTPException(
            status_code=503,
            detail="El directorio de imágenes FITS no está disponible",
        )

    except FrameImageError:
        # El FITS existe, pero no pudo convertirse correctamente.
        raise HTTPException(
            status_code=503,
            detail="No fue posible generar la imagen PNG del frame",
        )

@router.get("/frames", response_model=FramesResponse)
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
