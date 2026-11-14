from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    model_validator,
)


Band = Literal[
    "SPHEREx-D1",
    "SPHEREx-D2",
    "SPHEREx-D3",
    "SPHEREx-D4",
    "SPHEREx-D5",
    "SPHEREx-D6",
]


class IrsaQuery(BaseModel):
    # Rechaza valores especiales como NaN e infinito.
    model_config = ConfigDict(allow_inf_nan=False)

    ra: float = Field(
        ge=0,
        lt=360,
        description="Ascensión recta ICRS en grados",
    )
    dec: float = Field(
        ge=-90,
        le=90,
        description="Declinación ICRS en grados",
    )
    band: Band = "SPHEREx-D1"
    limit: int = Field(default=10, ge=1, le=100)


class IrsaObservation(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    start_mjd: float = Field(description="Inicio en días MJD")
    end_mjd: float = Field(description="Final en días MJD")
    start_utc: str = Field(description="Inicio ISO en UTC")
    band: Band
    cutout_url: HttpUrl

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.end_mjd < self.start_mjd:
            raise ValueError("El final es anterior al inicio")
        return self


class IrsaResponse(BaseModel):
    source: Literal["IRSA"] = "IRSA"
    query: IrsaQuery
    count: int = Field(ge=0)
    observations: list[IrsaObservation]

    @model_validator(mode="after")
    def validate_count(self):
        if self.count != len(self.observations):
            raise ValueError("El contador no coincide con la lista")

        if self.count > self.query.limit:
            raise ValueError("La respuesta supera el límite solicitado")

        return self