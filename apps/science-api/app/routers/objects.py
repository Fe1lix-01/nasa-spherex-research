# APIRouter permite definir rutas en un archivo separado.
# HTTPException permite responder con errores HTTP controlados.
from fastapi import APIRouter, HTTPException

# Modelos utilizados para validar las respuestas.
from app.schemas.objects import (
    AstronomicalObjectDetail,
    ObjectsResponse,
)
# Servicio que contiene la lógica de agrupación y búsqueda.
from app.services import objects as objects_service


router = APIRouter(
    # Prefijo compartido por las rutas de este router.
    prefix="/api/v1",
    # Agrupa los endpoints bajo "Objects" en Swagger.
    tags=["Objects"],
)

# La ruta completa será:
# GET /api/v1/objects
#
# response_model indica la estructura de la respuesta.
@router.get(
    "/objects",
    response_model=ObjectsResponse,
)
def get_objects(q: str | None = None):
      # Como q no aparece en la ruta y tiene un valor simple,
    # FastAPI lo recibe como parámetro de consulta.
    #
    # Ejemplo:
    # /api/v1/objects?q=SIMP
    #
    # Por eso Swagger muestra el campo q.
    try:
        # Entrega la búsqueda al servicio.
        objects = objects_service.list_objects(q=q)
    except OSError:
        # Incluye FileNotFoundError:
        # por ejemplo, cuando falta el directorio de datos.
        #
        # No enviamos al cliente el texto original del error,
        # porque podría contener rutas locales.
        raise HTTPException(
            status_code=503,
            detail="El catálogo local de observaciones no está disponible",
        ) from None
    except ValueError:
         # El servicio no pudo interpretar algún nombre.
        raise HTTPException(
            status_code=503,
            detail="El catálogo local contiene nombres de archivo no reconocidos",
        ) from None

# FastAPI valida esta estructura usando ObjectsResponse
    # y la convierte en una respuesta JSON.
    #
    # El modelo del listado excluye las observaciones
    # individuales y publica únicamente el resumen.
    return {
        "total": len(objects),
        "objects": objects,
    }

# Las llaves indican un parámetro de ruta.
#
# Ejemplo:
# /api/v1/objects/identificador-del-objeto
@router.get(
    "/objects/{object_id}",
    response_model=AstronomicalObjectDetail,
)
def get_object_by_id(object_id: str):
    try:
        # Busca el objeto utilizando el servicio.
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
    # None significa que el catálogo se pudo consultar,
    # pero ese identificador no pertenece a ningún objeto.

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Objeto astronómico no encontrado",
        )
    # El modelo de detalle incluye las observaciones
    return item