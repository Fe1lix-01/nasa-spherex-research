import pytest
from pydantic import ValidationError

from app.schemas.objects import (
    AstronomicalObjectDetail,
    AstronomicalObjectSummary,
    ObjectsResponse,
)


def summary_data(local=0, remote=0):
    return {
        "id": "example-object",
        "name": "Objeto de prueba",
        "observation_count": local + remote,
        "local_observation_count": local,
        "remote_observation_count": remote,
        "detectors": [],
    }


@pytest.mark.parametrize(
    ("local", "remote"),
    [(0, 0), (6, 0), (0, 2), (6, 2)],
)
def test_summary_accepts_consistent_counts(local, remote):
    model = AstronomicalObjectSummary(
        **summary_data(local, remote)
    )

    assert model.observation_count == local + remote


@pytest.mark.parametrize("wrong_total", [0, 2, 99])
def test_summary_rejects_inconsistent_total(wrong_total):
    data = summary_data(local=1, remote=2)
    data["observation_count"] = wrong_total

    with pytest.raises(ValidationError, match="suma"):
        AstronomicalObjectSummary(**data)


def test_detail_accepts_matching_local_list():
    data = summary_data(local=1)
    data["detectors"] = ["D1"]
    data["observations"] = [
        {
            "id": "example-D1",
            "detector": "D1",
            "filename": "Objeto de prueba_D1_test.fits",
            "format": "FITS",
        }
    ]

    model = AstronomicalObjectDetail(**data)

    assert model.local_observation_count == len(model.observations)


def test_detail_rejects_missing_local_observations():
    data = summary_data(local=1)
    data["observations"] = []

    with pytest.raises(ValidationError, match="cantidad de observations"):
        AstronomicalObjectDetail(**data)


def test_detail_rejects_missing_remote_observations():
    data = summary_data(remote=1)
    data["observations"] = []
    data["remote_observations"] = []

    with pytest.raises(
        ValidationError,
        match="cantidad de remote_observations",
    ):
        AstronomicalObjectDetail(**data)


@pytest.mark.parametrize("count", [0, 1])
def test_objects_response_accepts_matching_total(count):
    objects = (
        [AstronomicalObjectSummary(**summary_data())]
        if count
        else []
    )

    model = ObjectsResponse(total=count, objects=objects)

    assert model.total == len(model.objects)


@pytest.mark.parametrize("wrong_total", [1, 3])
def test_objects_response_rejects_inconsistent_total(wrong_total):
    with pytest.raises(ValidationError, match="cantidad de objects"):
        ObjectsResponse(total=wrong_total, objects=[])

@pytest.mark.parametrize(
    "detector",
    ["D1", "D2", "D3", "D4", "D5", "D6"],
)
def test_summary_accepts_supported_detectors(detector):
    data = summary_data(local=1)
    data["detectors"] = [detector]

    model = AstronomicalObjectSummary(**data)

    assert model.detectors == [detector]


@pytest.mark.parametrize(
    "detector",
    ["D0", "D7", "D9", "SPHEREx-D4"],
)
def test_summary_rejects_unsupported_detectors(detector):
    data = summary_data(local=1)
    data["detectors"] = [detector]

    with pytest.raises(ValidationError):
        AstronomicalObjectSummary(**data)