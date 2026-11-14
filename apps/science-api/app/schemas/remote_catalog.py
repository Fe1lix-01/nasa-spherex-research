from typing import Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    model_validator,
)

from app.schemas.sia import SiaResponse


class RemoteTarget(BaseModel):
    """Objeto y procedencia de la posición utilizada en la consulta."""

    model_config = ConfigDict(extra="forbid")

    name: Literal["M101"]
    position_source: str = Field(min_length=1)
    reference_product_url: HttpUrl


class SpatialAssociation(BaseModel):
    """Relación documentada entre el objeto y las imágenes encontradas."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["spatial_intersection"]
    description: str = Field(min_length=1)


class RemoteCatalogSnapshot(BaseModel):
    """Registro local de una consulta real de metadatos SIA."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    queried_at_utc: AwareDatetime
    target: RemoteTarget
    association: SpatialAssociation
    result: SiaResponse

    @model_validator(mode="after")
    def validate_observations(self):
        """Comprueba la unicidad de los productos del registro."""
        # SiaResponse valida la coherencia de colección y banda.
        product_ids: set[str] = set()

        for observation in self.result.observations:
            if observation.product_id in product_ids:
                raise ValueError(
                    "El registro contiene productos duplicados."
                )

            product_ids.add(observation.product_id)

        return self