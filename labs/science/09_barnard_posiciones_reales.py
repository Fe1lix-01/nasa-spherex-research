"""Práctica 9: calcular la posición REAL de Barnard en cada una de las 5 fechas descargadas.

No detecta la estrella dentro de la imagen (eso necesitaría un algoritmo de detección de
fuentes). En vez de eso, usa el movimiento propio de Barnard, que es uno de los datos
astronómicos mejor medidos que existen, y calcula dónde estaba la estrella exactamente en
cada fecha real de observación. Es el mismo método que usan los catálogos profesionales
para predecir la posición de una estrella en cualquier fecha.

Valores de referencia (J2000, catálogo ICRS; ver Wikipedia/Hipparcos-Gaia):
  RA = 269.452077 °, Dec = 4.693364 °
  Movimiento propio: pmRA*cos(Dec) = -801.551 mas/año, pmDec = 10362.394 mas/año
  Paralaje: 546.9759 mas

Lee manifest.json (de la práctica 7) y le agrega, a cada época, la posición real calculada
en esa fecha exacta.
"""

import json
from pathlib import Path

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

# Catálogo de referencia de Barnard (J2000), con su movimiento propio.
REF_EPOCH = Time("J2000")
REF_COORD = SkyCoord(
    ra=269.452077 * u.deg,
    dec=4.693364 * u.deg,
    pm_ra_cosdec=-801.551 * u.mas / u.yr,
    pm_dec=10362.394 * u.mas / u.yr,
    distance=(1 / (546.9759e-3)) * u.pc,  # paralaje 546.9759 mas -> distancia en parsecs
    obstime=REF_EPOCH,
    frame="icrs",
)


def position_at(date_utc: str) -> tuple[float, float]:
    """RA/Dec reales (grados) de Barnard en la fecha dada, por su movimiento propio."""
    target_epoch = Time(date_utc, scale="utc")
    moved = REF_COORD.apply_space_motion(new_obstime=target_epoch)
    return float(moved.ra.deg), float(moved.dec.deg)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    manifest_path = base_dir / "outputs" / "practica07_barnard" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No encuentro el manifiesto de la práctica 7.\n{manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    print("Época | fecha real | posición pedida (centro del recorte) | posición real (movimiento propio)")
    for entry in manifest:
        ra_real, dec_real = position_at(entry["observedAtUtc"])
        print(
            f"{entry['epochId']} | {entry['observedAtUtc']} | "
            f"RA={entry['ra']:.5f}, Dec={entry['dec']:.5f} | "
            f"RA={ra_real:.5f}, Dec={dec_real:.5f}"
        )
        entry["raReal"] = ra_real
        entry["decReal"] = dec_real

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifiesto actualizado (con raReal/decReal) en: {manifest_path}")


if __name__ == "__main__":
    main()
