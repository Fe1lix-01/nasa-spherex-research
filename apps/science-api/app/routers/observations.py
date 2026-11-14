from fastapi import APIRouter, HTTPException
from app.services.observations import list_observations
from app.schemas.observations import ObservationsResponse

router = APIRouter(
    prefix='/api/v1',
    tags=['Observations']
)

@router.get(
        "/observations",
        response_model = ObservationsResponse                   ## Le indicamos a FastApi que estructura debe tener la respuesta ##        
)
def get_observations():
    try:
        observations = list_observations()

        return {
            "total": len(observations),                         ## Construimos la respuesta y cuenta cuantos archivos encontramos ##        
            "observations": observations
        }

    except FileNotFoundError:                                   ## Manejo de errores HTTPS, si la carpeta no existe se lanza el FileNotFoundError##
        raise HTTPException(                                   ## Convertimos la respuesta controlada HTTPS sin mostrar rutas internas ##
            status_code=503, 
            detail="El catalogo local de observaciones no esta disponible"
        )

    