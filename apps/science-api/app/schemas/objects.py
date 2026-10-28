from pydantic import BaseModel, Field

from app.schemas.observations import Observations


class AstronomicalObjectSummary(BaseModel):
    id: str
    name: str
    observation_count: int = Field(ge=0)
    detectors: list[str]


class AstronomicalObjectDetail(AstronomicalObjectSummary):
    observations: list[Observations]


class ObjectsResponse(BaseModel):
    total: int = Field(ge=0)
    objects: list[AstronomicalObjectSummary]