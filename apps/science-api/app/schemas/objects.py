# La importacion de BaseModel permite definir modelos de datos con Pydantic.
# Y la importacion de Field permite agregar restricciones a sus campos.
from pydantic import BaseModel, Field

# Aqui se reutilza el modelo de Observacion que ya existe.
# De esta manera no se repite la definicion de sus campos.
from app.schemas.observations import Observations

# Esta clase represnta el resumen de un objeto astronomico.
# y pues es la informacion que aparece en el listado :V.
class AstronomicalObjectSummary(BaseModel):
    # Se sabe q este es el identificador del objeto.
    id: str
    # Nombre del objeto.
    name: str
    #Cantidad de los archivos asociados.
    observation_count: int = Field(ge=0)
    # Lista de detectores disponibles.
    # Ejemplo: ["D1", "D2", "D3"].
    detectors: list[str]

# Hereda todos los campos del resumen:
# id, name, observation_count y detectors.
#
# Además, agrega las observaciones individuales.
# Se usa para consultar un objeto por su ID.
class AstronomicalObjectDetail(AstronomicalObjectSummary):
    observations: list[Observations]

# Representa la respuesta del listado completo.
class ObjectsResponse(BaseModel):
     # Cantidad de OBJETOS encontrados después del filtro.
    # No es la cantidad de archivos FITS.
    total: int = Field(ge=0)
    # Lista de resúmenes de los objetos encontrados.
    objects: list[AstronomicalObjectSummary]