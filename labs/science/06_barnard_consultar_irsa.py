
"""Práctica 6: consultar observaciones SPHEREx de Barnard.

Basado en el tutorial oficial de IRSA.
Esta práctica NO descarga imágenes FITS.
"""

import argparse
import csv
from pathlib import Path

# Centro aproximado de Barnard para 2026.
# No es una predicción astrométrica de precisión.
DEFAULT_RA = 269.44627
DEFAULT_DEC = 4.76820


def build_query(ra, dec, detector, limit):
    bandpass = f"SPHEREx-{detector}"

    return f"""
SELECT TOP {limit}
    a.uri AS artifact_uri,
    p.time_bounds_lower AS observation_mjd,
    p.energy_bandpassname AS bandpass
FROM spherex.artifact a
JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(
    POINT('ICRS', {ra}, {dec}), p.poly
)
AND p.energy_bandpassname = '{bandpass}'
""".strip()


def main():
    parser = argparse.ArgumentParser(
        description="Consultar SPHEREx - Barnard"
    )

    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--ra", type=float, default=DEFAULT_RA)
    parser.add_argument("--dec", type=float, default=DEFAULT_DEC)

    parser.add_argument(
        "--detector",
        choices=[f"D{i}" for i in range(1, 7)],
        default="D2"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=500
    )

    args = parser.parse_args()

    if not (0 <= args.ra < 360 and -90 <= args.dec <= 90):
        parser.error("Coordenadas fuera de rango")

    if not (1 <= args.max_results <= 10000):
        parser.error("Límite de resultados inválido")

    query = build_query(
        args.ra,
        args.dec,
        args.detector,
        args.max_results
    )

    print(f"RA: {args.ra:.5f} grados")
    print(f"DEC: {args.dec:.5f} grados")
    print(f"Detector: {args.detector}")

    print("\nConsulta ADQL:")
    print(query)

    if args.dry_run:
        print("\nModo de prueba: no se consultó IRSA.")
        return

    from astroquery.ipac.irsa import Irsa
    from astropy.time import Time

    print("\nConsultando NASA IRSA...")

    try:
        response = Irsa.query_tap(
            query,
            async_job=True,
            maxrec=500
        )

        table = (
            response.to_table()
            if hasattr(response, "to_table")
            else response
        )

    except Exception as error:
        raise SystemExit(
            f"Error consultando IRSA: {error}"
        ) from error

    print(f"\nObservaciones encontradas: {len(table)}")

    if len(table) == 0:
        print("No se encontraron observaciones.")
        return

    output_dir = Path(
        "labs/science/outputs/practica06_barnard"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"barnard_{args.detector}.csv"

    records = []


    for row in table:
        mjd = float(row["observation_mjd"])

        # Convertimos la fecha MJD a UTC.
        utc = Time(mjd, format="mjd").isot

        records.append({
            "observation_mjd": mjd,
            "observation_utc": utc,
            "bandpass": str(row["bandpass"]),
            "artifact_uri": str(row["artifact_uri"])
        })

    records.sort(key=lambda item: item["observation_mjd"])

    with output_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0].keys())
        )

        writer.writeheader()
        writer.writerows(records)

    print("\nPrimeras observaciones:")

    for item in records[:5]:
        print(
            item["observation_utc"],
            "|",
            item["bandpass"]
        )

    print(f"\nCSV guardado en: {output_path}")

    if len(records) >= args.max_results:
        print("Aviso: se alcanzó el límite de resultados.")

    print("No se descargaron archivos FITS.")


if __name__ == "__main__":
    main()
