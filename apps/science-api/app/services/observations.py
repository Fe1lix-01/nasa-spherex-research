import re

from app.core.paths import FITS_DIR


def list_observations():
    observations = []

    if not FITS_DIR.is_dir():
        raise FileNotFoundError(
            f"No existe el directorio: {FITS_DIR}"
        )

    for file in sorted(FITS_DIR.glob("*.fits")):
        detector_match = re.search(r"_D([1-6])_", file.name)

        if detector_match is None:
            continue

        observations.append({
            "id": file.name,
            "detector": f"D{detector_match.group(1)}",
            "filename": file.name,
            "format": "FITS"
        })

    return observations
