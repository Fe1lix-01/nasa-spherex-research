from pydantic import BaseModel
from typing import Literal

class Observations(BaseModel):                          ## Definimos como debe verse una observacion individual ##
    id: str
    detector: Literal['D1','D2','D3','D4','D5','D6']
    filename: str
    format: Literal['FITS']

class ObservationsResponse(BaseModel):                ## Definimos la respuesta completa del endpoint ##
    total: int
    observations: list[Observations]