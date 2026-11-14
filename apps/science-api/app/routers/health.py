from fastapi import APIRouter

router = APIRouter(         ## Creamos rutas independientes de main.py ##
    prefix='/api/v1',       ## Añadimos el prefijo comun a las rutas de este router ##
    tags=['Health']        ## Agrupamos los endpoints en Swagger ##
)

@router.get('/health')
def health_check():
    return{
        'status':'ok',
        'service':'ETER Backend'
    }