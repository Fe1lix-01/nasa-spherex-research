
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.wcs import WCS
from astropy.utils.data import download_file

url = (
    "https://irsa.ipac.caltech.edu/data/demos/"
    "notebooks/spherex/M101_irsa.fits"
)

# Reutiliza el FITS descargado en la caché de Astropy
archivo = download_file(url, cache=True)

Path("outputs").mkdir(exist_ok=True)

with fits.open(archivo) as hdul:
    # Elegimos el canal 63 (numeración desde 1)
    canal = 63
    indice = canal - 1

    imagen = hdul["IMAGE"].data[indice].copy()
    hits = hdul["NHITS"].data[indice].copy()
    flags = hdul["FLAGS"].data[indice].copy()

    # Leer la información de los 102 canales
channels = hdul["SPECTRAL_CHANNELS"].data

# Obtener la longitud de onda central del canal 63
longitud_onda = float(channels["WAVELENGTH"][indice])

    # WCS espacial
wcs = WCS(hdul["IMAGE"].header, fobj=hdul).celestial

    # Revisar fechas en todos los encabezados
print("\n--- METADATOS TEMPORALES ---")
for hdu in hdul:
        for key in ["DATE-OBS", "DATE-END", "MJD-OBS"]:
            if key in hdu.header:
                print(hdu.name, key, hdu.header[key])

# Bits de calidad documentados por IRSA
overflow = (flags & (1 << 1)) != 0
outlier = (flags & (1 << 19)) != 0
source = (flags & (1 << 21)) != 0

# Máscara de píxeles utilizables para esta inspección
validos = (
    np.isfinite(imagen)
    & (hits > 0)
    & ~overflow
    & ~outlier
)

imagen_limpia = np.where(validos, imagen, np.nan)

print("\n--- CANAL SELECCIONADO ---")
print("Canal:", canal)
print("Longitud de onda:", longitud_onda, "micras")
print("Forma:", imagen.shape)
print("Pixeles validos:", np.sum(validos))
print("Pixeles overflow:", np.sum(overflow))
print("Pixeles outlier:", np.sum(outlier))
print("Pixeles fuente:", np.sum(source))

# Coordenadas celestes del centro
centro = wcs.pixel_to_world(133, 133)
print("RA central:", centro.ra.deg)
print("DEC central:", centro.dec.deg)

# Rango de visualización: no modifica datos físicos
vmin, vmax = np.nanpercentile(
    imagen_limpia, [5, 99.5]
)

fig, axes = plt.subplots(1, 3, figsize=(14, 4))

axes[0].imshow(
    imagen_limpia,
    origin="lower",
    cmap="inferno",
    vmin=vmin,
    vmax=vmax
)
axes[0].set_title(f"M101 - Canal {canal}")

axes[1].imshow(hits, origin="lower", cmap="viridis")
axes[1].set_title("Cobertura NHITS")

axes[2].imshow(
    validos,
    origin="lower",
    cmap="gray",
    vmin=0,
    vmax=1
)
axes[2].set_title("Mascara de calidad")

for ax in axes:
    ax.set_xlabel("X [pixeles]")
    ax.set_ylabel("Y [pixeles]")

plt.suptitle(f"SPHEREx M101 - {longitud_onda:.3f} um")
plt.tight_layout()
plt.savefig("outputs/11_m101_canal_63.png", dpi=180)
plt.show()
