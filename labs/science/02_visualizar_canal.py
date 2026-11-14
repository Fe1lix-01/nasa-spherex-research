from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.wcs import WCS
from astropy.utils.data import download_file

# --------------------------------------------------
# 1. CARGAR CUBO SPHEREx M101
# --------------------------------------------------

url = (
    "https://irsa.ipac.caltech.edu/data/demos/"
    "notebooks/spherex/M101_irsa.fits"
)

archivo = download_file(url, cache=True)

carpeta_salida = Path(__file__).resolve().parent / "outputs"
carpeta_salida.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# 2. INSPECCIONAR CANAL ESPECTRAL
# --------------------------------------------------

canal = 63
indice = canal - 1

with fits.open(archivo) as hdul:

    hdul.info()

    # Extraer el plano correspondiente al canal
    imagen = hdul["IMAGE"].data[indice].copy()
    hits = hdul["NHITS"].data[indice].copy()
    flags = hdul["FLAGS"].data[indice].copy()

    # Consultar la tabla de canales espectrales
    channels = hdul["SPECTRAL_CHANNELS"].data

    longitud_onda = float(
        channels["WAVELENGTH"][indice]
    )

    # Extraer WCS espacial (RA y DEC)
    wcs = WCS(
        hdul["IMAGE"].header,
        fobj=hdul
    ).celestial

    # Consultar metadatos temporales
    print("\n--- METADATOS TEMPORALES ---")

    for hdu in hdul:
        for key in ["DATE-OBS", "DATE-END", "MJD-OBS"]:
            if key in hdu.header:
                print(hdu.name, key, hdu.header[key])

# --------------------------------------------------
# 3. INTERPRETAR BANDERAS DE CALIDAD
# --------------------------------------------------

overflow = (flags & (1 << 1)) != 0
outlier = (flags & (1 << 19)) != 0
source = (flags & (1 << 21)) != 0

# Mascara de pixeles utilizables
validos = (
    np.isfinite(imagen)
    & (hits > 0)
    & ~overflow
    & ~outlier
)

imagen_limpia = np.where(validos, imagen, np.nan)

# --------------------------------------------------
# 4. MOSTRAR INFORMACION CIENTIFICA
# --------------------------------------------------

print("\n--- CANAL SELECCIONADO ---")

print("Canal:", canal)
print("Longitud de onda:", longitud_onda, "micras")
print("Dimensiones:", imagen.shape)
print("Pixeles validos:", np.sum(validos))
print("Pixeles overflow:", np.sum(overflow))
print("Pixeles outlier:", np.sum(outlier))
print("Pixeles fuente:", np.sum(source))

# Coordenadas del centro de la imagen
centro_x = (imagen.shape[1] - 1) / 2
centro_y = (imagen.shape[0] - 1) / 2

centro = wcs.pixel_to_world(centro_x, centro_y)

print("\n--- COORDENADAS CENTRALES ---")
print("RA:", centro.ra.deg)
print("DEC:", centro.dec.deg)

# --------------------------------------------------
# 5. VISUALIZAR IMAGEN Y COBERTURA
# --------------------------------------------------

if not np.any(validos):
    raise ValueError(
        "No hay pixeles validos para visualizar este canal."
    )

vmin, vmax = np.nanpercentile(
    imagen_limpia, [5, 99.5]
)

fig, axes = plt.subplots(
    1, 3, figsize=(14, 4)
)

# Imagen cientifica
im0 = axes[0].imshow(
    imagen_limpia,
    origin="lower",
    cmap="inferno",
    vmin=vmin,
    vmax=vmax
)

axes[0].set_title(f"M101 - Canal {canal}")

fig.colorbar(
    im0,
    ax=axes[0],
    label="MJy/sr",
    fraction=0.046
)

# Numero de contribuciones
axes[1].imshow(
    hits,
    origin="lower",
    cmap="viridis"
)

axes[1].set_title("Cobertura NHITS")

# Mascara de calidad
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

plt.suptitle(
    f"SPHEREx M101 - {longitud_onda:.3f} um"
)

plt.tight_layout()

ruta_salida = carpeta_salida / "11_m101_canal_63.png"

plt.savefig(ruta_salida, dpi=180)

print("\nImagen guardada en:", ruta_salida)

plt.show()
