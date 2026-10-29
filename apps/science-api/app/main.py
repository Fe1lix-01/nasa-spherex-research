from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware        ## Compenente que configura la comunicacion entre el navegador y la API ##
from app.routers import health, observations, objects

app = FastAPI(
    title="ETER API",
    description="Backend científico de ETER",
    version="0.1.0",
)

app.add_middleware(                       ## Compenente intermediario de solicitudes  y respuestas antes de llegar al endpoint o  regresen al cliente ##
    CORSMiddleware,
    allow_origins=[                      ## Origines permitidos durante el desarrollo ##
        "http://localhost:3000",         ## Interfaz que ve el usuario ##
        "http://127.0.0.1:3000",         ## API que entrega los datos ##
    ],
    allow_credentials=True,              ## Permite solicitudes con credenciales ##
    allow_methods=["*"],                 ## Perminte todos los metodos HTTPS mendiante CORS ##
    allow_headers=["*"],                 ## Permite que las solicitudes incluyan distintos encabezados HTTP ##
)

app.include_router(health.router)
app.include_router(observations.router)
app.include_router(objects.router)