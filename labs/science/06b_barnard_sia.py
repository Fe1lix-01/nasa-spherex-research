
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astroquery.ipac.irsa import Irsa

# Centro aproximado de Barnard en 2026
coord = SkyCoord(
    ra=269.44627 * u.deg,
    dec=4.76820 * u.deg,
    frame="icrs"
)

# Buscar en un pequeño entorno de la posición
radius = 30 * u.arcsec

for collection in ["spherex_qr2", "spherex_qr3"]:
    print(f"\nConsultando {collection}...")

    try:
        results = Irsa.query_sia(
            pos=(coord, radius),
            collection=collection
        )
    except Exception as error:
        print("Error:", error)
        continue

    print("Registros encontrados:", len(results))

    d2 = [
        row for row in results
        if str(row["energy_bandpassname"]).strip()
        == "SPHEREx-D2"
    ]

    print("Observaciones D2:", len(d2))

    for row in d2[:10]:
        mjd = float(row["t_min"])
        fecha = Time(mjd, format="mjd", scale="utc").isot

        print(
            "Fecha:", fecha,
            "| Detector:", row["energy_bandpassname"]
        )