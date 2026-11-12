import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "science-api"))

from app.schemas.sia import SiaQuery
from app.services.sia import list_sia_observations


def main() -> None:
    # Posición contrastada con el centro WCS del cubo oficial de M101.
    query = SiaQuery(
        collection="spherex_qr2",
        ra=210.8022671,
        dec=54.34895,
        radius_arcsec=30,
        band="SPHEREx-D4",
        limit=2,
    )

    # Reutilizamos el servicio del backend.
    response = list_sia_observations(query)

    product_ids = [
        observation.product_id
        for observation in response.observations
    ]

    if len(product_ids) != len(set(product_ids)):
        raise ValueError("IRSA devolvió identificadores de producto duplicados.")

    record = {
        "schema_version": 1,
        "queried_at_utc": datetime.now(timezone.utc).isoformat(),
        "target": {
            "name": "M101",
            "position_source": (
                "Centro WCS inspeccionado del cubo oficial M101_irsa.fits"
            ),
            "reference_product_url": (
                "https://irsa.ipac.caltech.edu/data/demos/"
                "notebooks/spherex/M101_irsa.fits"
            ),
        },
        "association": {
            "type": "spatial_intersection",
            "description": (
                "La cobertura de la imagen intersecta el círculo consultado."
            ),
        },
        "result": response.model_dump(mode="json"),
    }

    destination = PROJECT_ROOT / "data" / "m101" / "observations.json"
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Publicamos el archivo únicamente cuando terminó de escribirse.
    temporary = None

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary = Path(output.name)
            json.dump(record, output, ensure_ascii=False, indent=2)

        temporary.replace(destination)

    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    print("Observaciones guardadas:", response.count)
    print("Archivo:", destination)

    for observation in response.observations:
        print(observation.product_id)


if __name__ == "__main__":
    main()