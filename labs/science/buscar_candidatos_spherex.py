
from astroquery.ipac.irsa import Irsa
from astropy.coordinates import SkyCoord
import astropy.units as u
import csv

# Una de las posiciones compartidas encontradas
RA = 295.4097841
DEC = -15.2231692

target = SkyCoord(RA, DEC, unit="deg")

print("Consultando observaciones SPHEREx...")

resultados = Irsa.query_sia(
    pos=(target, 1 * u.arcsec),
    collection=["spherex_dr1", "spherex_qr3"]
)

candidatos = []

for fila in resultados:
    url = str(fila["access_url"])
    obs_id = str(fila["obs_id"])

    # Solo detector 6
    if "/6/" not in url:
        continue

    # Solo observaciones de las dos campañas
    if not (
        "2025" in obs_id
        or "2026" in obs_id
    ):
        continue

    candidatos.append({
        "obs_id": obs_id,
        "mjd": str(fila["t_min"]),
        "url": url
    })

candidatos.sort(
    key=lambda x: x["mjd"]
)

print("\nObservaciones D6 encontradas:",
      len(candidatos))

for c in candidatos:
    print(c["obs_id"], "| MJD:", c["mjd"])

with open(
    "candidatos_d6.csv",
    "w",
    newline="",
    encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["obs_id", "mjd", "url"]
    )
    writer.writeheader()
    writer.writerows(candidatos)

print("\nGuardado: candidatos_d6.csv")
