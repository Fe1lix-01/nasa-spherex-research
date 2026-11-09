import pytest

from astropy.io import fits
from fastapi.testclient import TestClient

from app.main import app
from app.services import frames as frames_service


client = TestClient(app)


def test_get_frames():
    response = client.get("/api/v1/frames")

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 6
    assert len(data["frames"]) == 6

    detectors = {
        frame["detector"]
        for frame in data["frames"]
    }

    assert detectors == {
        "D1", "D2", "D3",
        "D4", "D5", "D6"
    }

    for frame in data["frames"]:
        assert frame["width"] == 16
        assert frame["height"] == 16

        assert 0.02 < frame["fov_x_deg"] < 0.04
        assert 0.02 < frame["fov_y_deg"] < 0.04

        assert 24.0 < frame["center_ra_deg"] < 25.0
        assert 9.0 < frame["center_dec_deg"] < 10.0

        assert frame["coordinate_system"] == "ICRS"
        assert frame["projection"] == "TAN"


def test_list_frames_missing_directory(monkeypatch, tmp_path):
    missing_dir = tmp_path / "missing"

    monkeypatch.setattr(
        frames_service,
        "FITS_DIR",
        missing_dir
    )

    with pytest.raises(FileNotFoundError):
        frames_service.list_frames()


def test_list_frames_rejects_fits_without_wcs(
    monkeypatch,
    tmp_path
):
    fits_dir = tmp_path / "fits"
    fits_dir.mkdir()

    invalid_file = fits_dir / "test_D1_100_arcsec_cutout.fits"

    hdu = fits.PrimaryHDU(
        data=[[0.0] * 16 for _ in range(16)]
    )

    hdu.writeto(invalid_file)

    monkeypatch.setattr(
        frames_service,
        "FITS_DIR",
        fits_dir
    )

    with pytest.raises(
        frames_service.FrameMetadataError,
        match="WCS"
    ):
        frames_service.list_frames()
