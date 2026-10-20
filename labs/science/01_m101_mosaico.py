
from pathlib import Path 
import numpy as np
import matplotlib.pyplot as plt

from astropy.io import fits
from astropy.utils.data import download_file

# Mosaico real preparado por IRSA para su tutorial
URL = (
    "https://irsa.ipac.caltech.edu/data/demos/"
    "notebooks/spherex/M101_irsa.fits"
)

output = Path("labs/science/outputs")
output.mkdir(parents=True, exist_ok=True)

print("1. Obteniendo cubo M101 desde IRSA...")

# Astropy conserva el archivo descargado en caché
file_path = download_file(
    URL,
    cache=True,
    show_progress=True,
    timeout=180
)

print("2. Abriendo archivo FITS...")

with fits.open(file_path) as hdul:

    hdul.info()

    cube = hdul["IMAGE"].data
    header = hdul["IMAGE"].header

    print("\nForma del cubo:", cube.shape)
    print("Unidades:", header.get("BUNIT", "No indicadas"))

    # Canal 63 en la numeración de FITS/tutorial:
    # índice 62 en Python
    plane_index = 62

    image = np.asarray(cube[plane_index], dtype=float)

    valid = image[np.isfinite(image)]

    if valid.size == 0:
        raise ValueError("La capa no contiene datos válidos.")

    vmin, vmax = np.percentile(valid, [5, 99])

    print("3. Dibujando la capa espectral 63...")

    plt.figure(figsize=(7, 6))

    plt.imshow(
        image,
        origin="lower",
        cmap="inferno",
        vmin=vmin,
        vmax=vmax
    )

    plt.colorbar(label=header.get("BUNIT", "Intensidad"))
    plt.title("M101 - SPHEREx - Canal 63")
    plt.xlabel("Píxel X")
    plt.ylabel("Píxel Y")

    destination = output / "m101_canal_63.png"

    plt.savefig(destination, dpi=160)
    plt.show()

    print("Imagen guardada en:", destination)
