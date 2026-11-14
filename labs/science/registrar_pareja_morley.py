
import csv
import warnings
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import map_coordinates
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.wcs import NoConvergence

RA = 295.4097841
DEC = -15.2231692

# Bits que indican problemas instrumentales importantes.
# No descartamos SOURCE solo por estar marcado.
BAD_BITS = (
    (1 << 0)   # TRANSIENT
    | (1 << 1) # OVERFLOW
    | (1 << 2) # SUR_ERROR
    | (1 << 6) # NONFUNC
    | (1 << 7) # DICHROIC
    | (1 << 9) # MISSING_DATA
    | (1 << 10) # HOT
)

with open(
    "parejas_ordenadas.csv",
    encoding="utf-8-sig"
) as f:
    parejas = list(csv.DictReader(f))

if not parejas:
    raise SystemExit("No hay parejas en el CSV")

mejor = min(
    parejas,
    key=lambda p: float(p["desajuste"])
)

def leer(campo):
    archivo = Path(mejor[campo])
    with fits.open(archivo) as h:
        img = h["IMAGE"].data.astype(float).copy()
        var = h["VARIANCE"].data.astype(float).copy()
        flags = h["FLAGS"].data.astype(np.int64).copy()
        wcs = WCS(
            h["IMAGE"].header, fobj=h
        ).celestial
        fecha = h["IMAGE"].header.get("DATE-OBS")
    return img, var, flags, wcs, fecha

a, va, fa, wa, fecha_a = leer("archivo_2025")
b, vb, fb, wb, fecha_b = leer("archivo_2026")

# Crear una cuadrícula usando los píxeles de 2025.
height, width = a.shape
y, x = np.indices(a.shape)

# Píxeles 2025 -> coordenadas celestes.
ra, dec = wa.pixel_to_world_values(
    x.ravel(), y.ravel()
)

# Coordenadas celestes -> píxeles 2026.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", UserWarning)
    try:
        xb, yb = wb.world_to_pixel_values(ra, dec)
    except NoConvergence as exc:
        solution = exc.best_solution
        xb = solution[:, 0]
        yb = solution[:, 1]

inside = (
    np.isfinite(xb)
    & np.isfinite(yb)
    & (xb >= 0)
    & (yb >= 0)
    & (xb < b.shape[1] - 1)
    & (yb < b.shape[0] - 1)
).reshape(a.shape)

xb = np.where(np.isfinite(xb), xb, -100)
yb = np.where(np.isfinite(yb), yb, -100)
coords = np.vstack([yb, xb])

# Reproyección exploratoria de la imagen de 2026.
b_aligned = map_coordinates(
    b, coords,
    order=1,
    mode="constant",
    cval=np.nan
).reshape(a.shape)

# Varianza interpolada, solo para comprobar validez.
# No es una propagación rigurosa de covarianzas.
vb_aligned = map_coordinates(
    vb, coords,
    order=1,
    mode="constant",
    cval=np.nan
).reshape(a.shape)

fb_aligned = map_coordinates(
    fb.astype(float), coords,
    order=0,
    mode="constant",
    cval=-1
).reshape(a.shape).astype(np.int64)

quality = (
    inside
    & np.isfinite(a)
    & np.isfinite(b_aligned)
    & np.isfinite(va)
    & np.isfinite(vb_aligned)
    & (va > 0)
    & (vb_aligned > 0)
    & ((fa & BAD_BITS) == 0)
    & ((fb_aligned & BAD_BITS) == 0)
)

print("\nMORLEY — REGISTRO WCS")
print("2025:", fecha_a)
print("2026:", fecha_b)
print("Píxeles con solape:", int(inside.sum()))
print("Píxeles que pasan filtros:", int(quality.sum()))
print("Desajuste espectral:", mejor["desajuste"])

# Misma escala visual para ambas imágenes.
values = np.concatenate([
    a[quality],
    b_aligned[quality]
])

if len(values) == 0:
    raise SystemExit(
        "No hay píxeles válidos en el solape"
    )

vmin, vmax = np.percentile(values, [5, 99])
if vmax <= vmin:
    vmax = vmin + 1.0

fig, axes = plt.subplots(
    1, 3, figsize=(13, 4.5)
)

axes[0].imshow(
    a, origin="lower",
    cmap="gray", vmin=vmin, vmax=vmax
)
axes[0].set_title("SPHEREx 2025")

axes[1].imshow(
    b_aligned, origin="lower",
    cmap="gray", vmin=vmin, vmax=vmax
)
axes[1].set_title("SPHEREx 2026 alineada")

axes[2].imshow(
    quality, origin="lower",
    cmap="gray", vmin=0, vmax=1
)
axes[2].set_title("Máscara de calidad")

# Posición de la coordenada elegida.
tx, ty = wa.world_to_pixel_values(RA, DEC)

for ax in axes[:2]:
    ax.plot(tx, ty, "r+", markersize=11)
    ax.set_xlabel("Pixel X")
    ax.set_ylabel("Pixel Y")

fig.tight_layout()
fig.savefig(
    "morley_registro_wcs.png",
    dpi=170
)
plt.show()

print("\nGuardado: morley_registro_wcs.png")
print("Esto NO es una detección ZOGY.")
