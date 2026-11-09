##Catalogar las imagenes con fechas, esto sirve en el front para las epocas y saber de que fecha se obtiene la imagen 
#Solo del canal D2
import csv
from collections import Counter
from pathlib import Path
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time
from astroquery.ipac.irsa import Irsa


RA = 269.44627 #RA es la ascensión recta, que indica una dirección sobre el cielo en sentido este-oeste dentro del sistema de coordenadas.
DEC = 4.76820 #Dec es la declinación, que indica una posición angular al norte o sur del ecuador celeste.
DETECTOR = "SPHEREx-D2" #DETECTOR representa el grupo instrumental que decidimos investigar.

OUTPUT = Path(
    "labs/science/outputs/practica07_barnard"
)

OUTPUT.mkdir(parents=True, exist_ok=True)

coord = SkyCoord(
    ra=RA * u.deg,
    dec=DEC * u.deg,
    frame="icrs", #Indica que trabajamos con el sistema (ICRS) Sistema internacional de Referencia Celeste
)

radius = 30 * u.arcsec #Radio de busqueda

observations = []

for release in ["spherex_qr2", "spherex_qr3"]:
    print(f"\nConsultando {release}...")

    try:
        table = Irsa.query_sia(
            pos=(coord, radius),
            collection=release,
        )
    except Exception as error:
        print(f"Error con {release}: {error}")
        continue

    print("Total de registros:", len(table))

    for row in table:
        band = str(row["energy_bandpassname"]).strip()

        if band != DETECTOR:
            continue

        mjd = float(row["t_min"])

        # MJD es una representación numérica
        # del tiempo utilizada en astronomía.
        date = Time(
            mjd, format="mjd", scale="utc" #MJD significa Modified Julian Date, o fecha juliana modificada.
        ).isot

        observations.append({ #Registro de cada imagen
            "release": release,
            "obs_id": str(row["obs_id"]),
            "date_utc": date,
            "mjd": mjd,
            "detector": band,
            "access_url": str(row["access_url"]),
        })

# Ordenamos las observaciones de más antigua a reciente.
observations.sort(key=lambda r: r["mjd"])

print("\nOBSERVACIONES D2:", len(observations))

if not observations:
    raise SystemExit("No hay observaciones para guardar.")

csv_path = OUTPUT / "barnard_observaciones_D2.csv"

with csv_path.open(
    "w", encoding="utf-8", newline=""
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=list(observations[0].keys()),
    )
    writer.writeheader()
    writer.writerows(observations)

# Agrupamos por versión y mes.
counts = Counter(
    (r["release"], r["date_utc"][:7])
    for r in observations
)

print("\nOBSERVACIONES POR MES")

for (release, month), total in sorted(counts.items()):
    print(f"{release} | {month} | {total}")

print("\nPRIMERAS 3 OBSERVACIONES")

for row in observations[:3]:
    print(row["release"], row["date_utc"], row["obs_id"])

print("\nÚLTIMAS 3 OBSERVACIONES")

for row in observations[-3:]:
    print(row["release"], row["date_utc"], row["obs_id"])

print("\nCSV generado:", csv_path)
print("No se han descargado archivos FITS.")
