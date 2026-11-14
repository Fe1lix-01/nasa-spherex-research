
import csv
import numpy as np
from pathlib import Path
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u

# Coordenadas de píxel aproximadas en la imagen 2025.
FUENTES = {
    "A": (22.0, 6.0),
    "B": (15.0, 4.0),
}

# Banderas problemáticas; SOURCE (21) no se rechaza.
BITS_MALOS = [0, 1, 2, 6, 7, 9, 10, 11, 14, 15, 17, 19, 20, 22]
BAD_MASK = sum(1 << bit for bit in BITS_MALOS)

with open("parejas_ordenadas.csv", encoding="utf-8-sig") as f:
    parejas = list(csv.DictReader(f))

if not parejas:
    raise SystemExit("No hay parejas en el CSV.")

pareja = min(
    parejas,
    key=lambda p: float(p["desajuste"])
)

def cargar(ruta):
    h = fits.open(Path(ruta))
    header = h["IMAGE"].header

    espacial = WCS(header, fobj=h).celestial
    espectral = WCS(header, fobj=h, key="W")
    espectral.sip = None

    return h, espacial, espectral

def evaluar(h, espectral, x, y):
    img = h["IMAGE"].data
    var = h["VARIANCE"].data
    flags = h["FLAGS"].data

    ny, nx = img.shape

    if not (
        np.isfinite(x) and np.isfinite(y)
        and 2 <= x < nx - 2
        and 2 <= y < ny - 2
    ):
        return None

    ix, iy = int(round(x)), int(round(y))

    # Ventana local de 5x5 píxeles
    imagen_local = img[iy-2:iy+3, ix-2:ix+3]
    var_local = var[iy-2:iy+3, ix-2:ix+3]
    flags_local = flags[iy-2:iy+3, ix-2:ix+3]

    calidad = (
        np.isfinite(imagen_local)
        & np.isfinite(var_local)
        & (var_local > 0)
        & ((flags_local & BAD_MASK) == 0)
    )

    wavelength, bandwidth = espectral.pixel_to_world(x, y)

    return {
        "lambda": float(np.asarray(
            wavelength.to_value(u.um)
        ).item()),
        "bandwidth": float(np.asarray(
            bandwidth.to_value(u.um)
        ).item()),
        "flags": int(flags[iy, ix]),
        "calidad": float(np.mean(calidad)),
    }

a, wa, sa = cargar(pareja["archivo_2025"])
b, wb, sb = cargar(pareja["archivo_2026"])

try:
    for nombre, (x1, y1) in FUENTES.items():

        # La misma posición celeste en ambas exposiciones
        ra, dec = wa.pixel_to_world_values(x1, y1)
        x2, y2 = wb.world_to_pixel_values(ra, dec)

        x2 = float(np.asarray(x2).item())
        y2 = float(np.asarray(y2).item())

        d1 = evaluar(a, sa, x1, y1)
        d2 = evaluar(b, sb, x2, y2)

        print("\n" + "=" * 50)
        print("FUENTE:", nombre)
        print(f"RA: {ra:.7f} | Dec: {dec:.7f}")
        print(f"Pixel 2025: ({x1:.2f}, {y1:.2f})")
        print(f"Pixel 2026: ({x2:.2f}, {y2:.2f})")

        if d1 is None or d2 is None:
            print("No hay margen suficiente en ambas imágenes.")
            continue

        ancho = (d1["bandwidth"] + d2["bandwidth"]) / 2

        desajuste = abs(
            d1["lambda"] - d2["lambda"]
        ) / ancho

        print(f"Lambda 2025: {d1['lambda']:.5f} um")
        print(f"Lambda 2026: {d2['lambda']:.5f} um")
        print(f"Desajuste relativo: {desajuste:.4f}")

        print(f"FLAGS central 2025: {d1['flags']}")
        print(f"FLAGS central 2026: {d2['flags']}")

        print(
            f"Calidad local 2025: {100*d1['calidad']:.1f}%"
        )
        print(
            f"Calidad local 2026: {100*d2['calidad']:.1f}%"
        )

        if desajuste < 0.25:
            print("PRESELECCIÓN: banda prometedora.")
        else:
            print("PRESELECCIÓN: revisar diferencia espectral.")

finally:
    a.close()
    b.close()
