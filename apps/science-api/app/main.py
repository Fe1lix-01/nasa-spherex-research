from fastapi import FastAPI
from app.routers import health
                                                 
app = FastAPI(                                          ## Creamos la instancia de la app (Aparece automaticamente en Swagger)##
    title='ETER API',
    description='Backend cientifico de ETER',
    version='0.1.0'
)

app.include_router(health.router)               ## Incluimos en la ruta principal todas la rutas del router health