from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import sia
from app.routers import remote_previews

# Importamos los tres módulos de rutas.
# Esta importación debe aparecer una sola vez.
from app.routers import health, observations, objects, irsa, frames, science_preview


app = FastAPI(
    title="ETER API",
    description="Backend científico de ETER",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(observations.router)
app.include_router(objects.router)
app.include_router(irsa.router)
app.include_router(frames.router)
app.include_router(science_preview.router)
app.include_router(sia.router)
app.include_router(remote_previews.router)