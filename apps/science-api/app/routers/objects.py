# APIRouter permite definir rutas independientes.
# HTTPException permite devolver errores HTTP controlados.
from fastapi import APIRouter, HTTPException

# Modelos de validación de las respuestas.
from app.schemas.objects import (
    AstronomicalObjectDetail,
    ObjectsResponse,
)

# Servicio que contiene la lógica del catálogo unificado.
from app.services import objects as objects_service

# Error específico al leer o validar el registro remoto.
from app.services.remote_catalog import RemoteCatalogError


# Router para los endpoints del catálogo de objetos.
router = APIRouter(
    prefix="/api/v1",
    tags=["Objects"],
)


@router.get(
    "/objects",
    response_model=ObjectsResponse,
)
def get_objects(q: str | None = None):
    """
    Devuelve el catálogo de objetos astronómicos.

    Permite filtrar por nombre mediante el parámetro q.
    """

    try:
        # Obtiene los objetos locales y remotos.
        objects = objects_service.list_objects(q=q)

    except RemoteCatalogError:
        # El registro remoto no existe, no se puede leer
        # o contiene información inválida.
        raise HTTPException(
            status_code=503,
            detail=(
                "El registro remoto de observaciones "
                "no está disponible o es inválido"
            ),
        ) from None

    except OSError:
        # Error al acceder al catálogo local.
        raise HTTPException(
            status_code=503,
            detail=(
                "El catálogo local de observaciones "
                "no está disponible"
            ),
        ) from None

    except ValueError:
        # Error al interpretar los nombres de archivos locales.
        raise HTTPException(
            status_code=503,
            detail=(
                "El catálogo local contiene nombres "
                "de archivo no reconocidos"
            ),
        ) from None

    # FastAPI valida el resultado con ObjectsResponse
    # y convierte los datos a JSON.
    return {
        "total": len(objects),
        "objects": objects,
    }


@router.get(
    "/objects/{object_id}",
    response_model=AstronomicalObjectDetail,
)
def get_object_by_id(object_id: str):
    """
    Devuelve el detalle de un objeto astronómico por su ID.
    """

    try:
        # Busca el objeto dentro del catálogo unificado.
        item = objects_service.get_object(object_id)

    except RemoteCatalogError:
        # El registro remoto no está disponible o es inválido.
        raise HTTPException(
            status_code=503,
            detail=(
                "El registro remoto de observaciones "
                "no está disponible o es inválido"
            ),
        ) from None

    except OSError:
        # Error al acceder al catálogo local.
        raise HTTPException(
            status_code=503,
            detail=(
                "El catálogo local de observaciones "
                "no está disponible"
            ),
        ) from None

    except ValueError:
        # Error al interpretar los nombres de archivos locales.
        raise HTTPException(
            status_code=503,
            detail=(
                "El catálogo local contiene nombres "
                "de archivo no reconocidos"
            ),
        ) from None

    # Si el catálogo se consultó correctamente, pero el ID
    # no existe, respondemos con un 404.
    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Objeto astronómico no encontrado",
        )

    # El modelo de detalle valida los campos locales y remotos.
    return item
