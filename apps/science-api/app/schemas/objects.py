# La importacion de BaseModel permite definir modelos de datos con Pydantic.
# Y la importacion de Field permite agregar restricciones a sus campos.
from typing import Self

from pydantic import BaseModel, Field, model_validator

# Aqui se reutilza el modelo de Observacion que ya existe.
# De esta manera no se repite la definicion de sus campos.
from app.schemas.observations import Detector, Observations

from app.schemas.remote_catalog import SpatialAssociation
from app.schemas.sia import SiaObservation, SiaQuery

# Esta clase represnta el resumen de un objeto astronomico.
# y pues es la informacion que aparece en el listado :V.
class AstronomicalObjectSummary(BaseModel):
    # Se sabe q este es el identificador del objeto.
    id: str
    # Nombre del objeto.
    name: str
    #Cantidad de los archivos asociados.
    observation_count: int = Field(ge=0)
    local_observation_count: int = Field(default=0, ge=0)
    remote_observation_count: int = Field(default=0, ge=0)
    # Lista de detectores disponibles.
    # Ejemplo: ["D1", "D2", "D3"].
    detectors: list[Detector]

    @model_validator(mode="after")
    def validate_observation_counts(self) -> Self:
        expected_total = (
            self.local_observation_count
            + self.remote_observation_count
        )

        if self.observation_count != expected_total:
            raise ValueError(
                "observation_count debe coincidir con la suma "
                "de local_observation_count y remote_observation_count"
            )

        return self

class SciencePreview(BaseModel):
    title: str
    description: str

# Hereda todos los campos del resumen:
# id, name, observation_count y detectors.
#
# Además, agrega las observaciones individuales.
# Se usa para consultar un objeto por su ID.
class AstronomicalObjectDetail(AstronomicalObjectSummary):
    observations: list[Observations]
    remote_observations: list[SiaObservation] = Field(default_factory=list)
    remote_association: SpatialAssociation | None = None
    remote_query: SiaQuery | None = None
    science_preview: SciencePreview | None = None

    @model_validator(mode="after")
    def validate_observation_lists(self) -> Self:
        if self.local_observation_count != len(self.observations):
            raise ValueError(
                "local_observation_count debe coincidir "
                "con la cantidad de observations"
            )

        if self.remote_observation_count != len(self.remote_observations):
            raise ValueError(
                "remote_observation_count debe coincidir "
                "con la cantidad de remote_observations"
            )

        return self
# Representa la respuesta del listado completo.
class ObjectsResponse(BaseModel):
     # Cantidad de OBJETOS encontrados después del filtro.
    # No es la cantidad de archivos FITS.
    total: int = Field(ge=0)
    # Lista de resúmenes de los objetos encontrados.
    objects: list[AstronomicalObjectSummary]

    @model_validator(mode="after")
    def validate_total(self) -> Self:
        if self.total != len(self.objects):
            raise ValueError(
                "total debe coincidir con la cantidad de objects"
            )

        return self