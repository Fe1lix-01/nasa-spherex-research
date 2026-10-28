from fastapi import APIRouter, HTTPException

from app.schemas.objects import (
    AstronomicalObjectDetail,
    ObjectsResponse,
)
from app.services import objects as objects_service


router = APIRouter(
    prefix="/api/v1",
    tags=["Objects"],
)


@router.get(
    "/objects",
    response_model=ObjectsResponse,
)
def get_objects(q: str | None = None):
    try:
        objects = objects_service.list_objects(q=q)
    except OSError:
        raise HTTPException(
            status_code=503,
            detail="El catálogo local de observaciones no está disponible",
        ) from None
    except ValueError:
        raise HTTPException(
            status_code=503,
            detail="El catálogo local contiene nombres de archivo no reconocidos",
        ) from None

    return {
        "total": len(objects),
        "objects": objects,
    }


@router.get(
    "/objects/{object_id}",
    response_model=AstronomicalObjectDetail,
)
def get_object_by_id(object_id: str):
    try:
        item = objects_service.get_object(object_id)
    except OSError:
        raise HTTPException(
            status_code=503,
            detail="El catálogo local de observaciones no está disponible",
        ) from None
    except ValueError:
        raise HTTPException(
            status_code=503,
            detail="El catálogo local contiene nombres de archivo no reconocidos",
        ) from None

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Objeto astronómico no encontrado",
        )

    return item