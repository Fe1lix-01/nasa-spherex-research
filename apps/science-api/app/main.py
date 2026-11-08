from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, observations, objects, irsa


app = FastAPI(
    title="ETER API",
    description="Backend científico de ETER",
    version="0.1.0",
)

app.add_middleware(                   ## Configuracion de CORS que permite la comunicacion de frontend ##
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Registro de los routers de la API.
app.include_router(health.router)
app.include_router(observations.router)
app.include_router(objects.router)
app.include_router(irsa.router)