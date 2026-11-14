# BaseModel permite definir modelos de datos con Pydantic.
# Field permite agregar restricciones y valores predeterminados.
from pydantic import BaseModel, Field

# Reutilizamos el modelo de observación local existente.
from app.schemas.observations import Observations

# Modelos que representan la información del catálogo remoto.
from app.schemas.remote_catalog import SpatialAssociation
from app.schemas.sia import SiaObservation, SiaQuery


class AstronomicalObjectSummary(BaseModel):
    """Información resumida de un objeto astronómico."""

    # Identificador estable y nombre del objeto.
    id: str
    name: str

    # Conteo total de observaciones locales y remotas.
    observation_count: int = Field(ge=0)

    # Conteos separados por procedencia.
    local_observation_count: int = Field(default=0, ge=0)
    remote_observation_count: int = Field(default=0, ge=0)

    # Detectores disponibles en las observaciones locales.
    detectors: list[str]


class SciencePreview(BaseModel):
    """Metadatos de la vista previa científica."""

    title: str
    description: str


class AstronomicalObjectDetail(AstronomicalObjectSummary):
    """Información completa de un objeto astronómico."""

    # Observaciones FITS disponibles localmente.
    observations: list[Observations]

    # Observaciones obtenidas del catálogo remoto SIA.
    remote_observations: list[SiaObservation] = Field(
        default_factory=list
    )

    # Información de asociación espacial del catálogo remoto.
    remote_association: SpatialAssociation | None = None

    # Parámetros utilizados en la consulta remota.
    remote_query: SiaQuery | None = None

    # Vista previa científica, cuando está disponible.
    science_preview: SciencePreview | None = None


class ObjectsResponse(BaseModel):
    """Respuesta del endpoint que lista los objetos."""

    # Cantidad de objetos después de aplicar el filtro.
    total: int = Field(ge=0)

    # Resúmenes de los objetos encontrados.
    objects: list[AstronomicalObjectSummary]
