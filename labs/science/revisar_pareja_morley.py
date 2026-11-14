
from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.wcs import WCS

RA = 295.4097841
DEC = -15.2231692

with open("parejas_ordenadas.csv", encoding="utf-8-sig") as f:
    parejas = list(csv.DictReader(f))

if not parejas:
    raise SystemExit("No hay parejas disponibles.")

parejas.sort(key=lambda p: float(p["desajuste"]))
mejor = parejas[0]

print("PAREJA SELECCIONADA:")
print(mejor["observacion_2025"])
print(mejor["observacion_2026"])
print("Desajuste:", mejor["desajuste"])
print("Dias:", mejor["dias"])

fig, axes = plt.subplots(1, 2, figsize=(10, 5))

for ax, epoca, campo in zip(
    axes,
    ["2025", "2026"],
    ["archivo_2025", "archivo_2026"]
):
    archivo = Path(mejor[campo])

    with fits.open(archivo) as hdul:
        imagen = np.asarray(hdul["IMAGE"].data, float)
        varianza = np.asarray(hdul["VARIANCE"].data, float)
        flags = hdul["FLAGS"].data
        hdr = hdul["IMAGE"].header

        wcs = WCS(hdr, fobj=hdul).celestial

        x, y = wcs.world_to_pixel_values(RA, DEC)
        x = float(np.asarray(x).item())
        y = float(np.asarray(y).item())

        alto, ancho = imagen.shape
        dentro = (
            np.isfinite(x)
            and np.isfinite(y)
            and 0 <= x < ancho
            and 0 <= y < alto
        )

        print(f"\nEPOCA {epoca}")
        print("Archivo:", archivo.name)
        print("Fecha:", hdr.get("DATE-OBS"))
        print("OBSID:", hdr.get("OBSID"))
        print("Dimensiones:", imagen.shape)
        print("Coordenada pixel:", x, y)
        print("Dentro de imagen:", dentro)
        print(
            "Pixeles con varianza valida:",
            np.sum(np.isfinite(varianza) & (varianza > 0))
        )
        print("Pixeles FLAGS=0:", np.sum(flags == 0))

        if dentro:
            ix, iy = int(round(x)), int(round(y))
            if 0 <= ix < ancho and 0 <= iy < alto:
                print("Flag central:", int(flags[iy, ix]))

        validos = imagen[np.isfinite(imagen)]
        vmin, vmax = np.percentile(validos, [5, 99])

        if vmax <= vmin:
            vmax = vmin + 1

        ax.imshow(
            imagen,
            origin="lower",
            cmap="gray",
            vmin=vmin,
            vmax=vmax
        )

        if dentro:
            ax.scatter(
                x, y,
                color="red",
                marker="+",
                s=140
            )

        ax.set_title(f"SPHEREx {epoca}")
        ax.set_xlabel("Pixel X")
        ax.set_ylabel("Pixel Y")

plt.tight_layout()
plt.savefig("revision_pareja.png", dpi=160)
plt.show()
