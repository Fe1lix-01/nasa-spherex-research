from fastapi import FastAPI

# Importamos los tres módulos de rutas.
# Esta importación debe aparecer una sola vez.
from app.routers import health, observations, objects
                                            
# Creamos la aplicación principal.
# Estos datos aparecen en la documentación de Swagger     
app = FastAPI(                                          
    title='ETER API',
    description='Backend cientifico de ETER',
    version='0.1.0'
)

# Registramos las rutas de cada módulo.
app.include_router(health.router)               
app.include_router(observations.router)

# Sin esta línea, las rutas de Objects no existirían
# en la aplicación y devolverían 404.
app.include_router(objects.router)