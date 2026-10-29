from pathlib import Path

import pyvo
from astropy.time import Time


def main():
    # Coordenadas de M101, usadas en el tutorial oficial.
    ra = 24.2412498
    dec = 9.5630705

    # Banda asociada al detector D2.
    bandpass = "SPHEREx-D1"

    # Se usará para construir enlaces de recortes.
    # En esta práctica NO descargamos esos recortes.
    cutout_size_deg = 0.025

    service = pyvo.dal.TAPService(
        "https://irsa.ipac.caltech.edu/TAP"
    )

    query = f"""
    SELECT TOP 100
        p.time_bounds_lower,
        p.time_bounds_upper,
        p.energy_bandpassname,
        'https://irsa.ipac.caltech.edu/' || a.uri
        || '?center={ra},{dec}d&size={cutout_size_deg}'
        AS cutout_url
    FROM spherex.artifact a
    JOIN spherex.plane p ON a.planeid = p.planeid
    WHERE 1 = CONTAINS(
        POINT('ICRS', {ra}, {dec}),
        p.poly
    )
    AND p.energy_bandpassname = '{bandpass}'
    ORDER BY p.time_bounds_lower
    """

    print(f"Posición consultada: RA={ra}, Dec={dec} grados")
    print(f"Banda solicitada: {bandpass}")
    print("Consultando IRSA...")

    table = service.search(query).to_table()

    print(f"\nFilas recibidas: {len(table)}")
    print("Límite de esta consulta: 100 filas")
    print("Columnas:", table.colnames)

    if len(table) == 0:
        print("No se encontraron resultados para estos filtros.")
        return

    # Las coordenadas buscadas no son necesariamente
    # las coordenadas del centro de cada imagen.
    table["query_ra_deg"] = [ra] * len(table)
    table["query_dec_deg"] = [dec] * len(table)

    # Convertir el inicio de cada observación de MJD
    # a una fecha legible, usando UTC.
    table["start_utc"] = Time(
        table["time_bounds_lower"],
        format="mjd",
        scale="utc",
    ).isot

    print("\nPrimeras cinco observaciones:")
    table[
        [
            "start_utc",
            "energy_bandpassname",
            "time_bounds_lower",
        ]
    ][:5].pprint(max_width=120)

    print("\nPrimer enlace de recorte:")
    print(table["cutout_url"][0])

    # Guardar los resultados junto al experimento.
    output_dir = Path(__file__).resolve().parent / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "observaciones_irsa.csv"
    table.write(output_file, format="ascii.csv", overwrite=True)

    print(f"\nResultados guardados en:\n{output_file}")


if __name__ == "__main__":
    main()