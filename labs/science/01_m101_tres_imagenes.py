
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from astropy.io import fits
from astropy.utils.data import download_file

# 1. Descargar cubo oficial de ejemplo
url = (
    "https://irsa.ipac.caltech.edu/data/demos/"
    "notebooks/spherex/M101_irsa.fits"
)

archivo = download_file(url, cache=True)

# 2. Leer extensiones FITS
with fits.open(archivo, memmap=False) as hdul:
    hdul.info()
    cube = hdul["IMAGE"].data.astype(float)
    hits = hdul["NHITS"].data
    flags = hdul["FLAGS"].data

    wave_data = hdul["WCS-WAVE"].data
    planes = np.asarray(wave_data["PLANE"][0], dtype=int)
    wavelengths = np.array([
        float(w[0])
        for w in wave_data["WAVELENGTHS"][0]
    ])

print("Forma del cubo:", cube.shape)

# 3. Crear mascara de calidad
# Bit 1: overflow; bit 19: outlier
bad_bits = (1 << 1) | (1 << 19)

covered = (hits > 0) & np.isfinite(cube)
bad = (flags & bad_bits) != 0
valid = covered & ~bad

# 4. Crear tabla por plano espectral
rows = []

for i in range(cube.shape[0]):
    n = np.count_nonzero(covered[i])

    median_hits = (
        float(np.median(hits[i][covered[i]]))
        if n else np.nan
    )

    flag_pct = (
        100 * np.count_nonzero(
            covered[i] & bad[i]
        ) / n if n else np.nan
    )

    rows.append({
        "plane": int(planes[i]),
        "wavelength_um": wavelengths[i],
        "NHITS_mediana": median_hits,
        "FLAGS_pct_problematicos": flag_pct,
        "cobertura_pct":
            100 * np.mean(covered[i])
    })

tabla = pd.DataFrame(rows)
print(tabla.to_string(index=False))

tabla.to_csv("tabla_102_bandas.csv", index=False)

# 5. Comparar 3 longitudes de onda
targets = [1.0, 2.2, 3.3]

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for ax, target in zip(axes, targets):
    i = np.argmin(np.abs(wavelengths - target))

    img = np.where(valid[i], cube[i], np.nan)

    if np.any(np.isfinite(img)):
        lo, hi = np.nanpercentile(img, [2, 99])

        ax.imshow(
            img, origin="lower",
            cmap="inferno", vmin=lo, vmax=hi
        )

    ax.set_title(f"{wavelengths[i]:.3f} micras")
    ax.set_xlabel("X (pixel)")
    ax.set_ylabel("Y (pixel)")

plt.tight_layout()
plt.savefig("tres_bandas.png", dpi=200)
plt.show()


def normalize_band(target):
    i = np.argmin(np.abs(wavelengths - target))
    img = np.where(valid[i], cube[i], np.nan)

    lo, hi = np.nanpercentile(img, [2, 99])
    scaled = (img - lo) / max(hi - lo, 1e-12)

    return np.nan_to_num(
        np.clip(scaled, 0, 1), nan=0.0
    )

rgb = np.dstack([
    normalize_band(3.3),  # Rojo
    normalize_band(2.2),  # Verde
    normalize_band(1.0)   # Azul
])

plt.figure(figsize=(7, 7))
plt.imshow(rgb, origin="lower")
plt.title("SPHEREx M101 - RGB falso color")
plt.axis("off")
plt.savefig("rgb_spherex.png", dpi=200)
plt.show()
