from astropy.io import fits
from astropy.table import Table
import numpy as np

url = (
    "https://irsa.ipac.caltech.edu/data/demos/"
    "notebooks/spherex/M101_irsa.fits"
)

with fits.open(url) as hdul:
    # Mostrar estructura del FITS
    hdul.info()

    cube = hdul["IMAGE"].data
    header = hdul["IMAGE"].header
    hits = hdul["NHITS"].data
    flags = hdul["FLAGS"].data

    print("\n--- INFORMACION DEL CUBO ---")
    print("Dimensiones:", cube.shape)
    print("Unidades:", header.get("BUNIT"))
    print("Canales:", cube.shape[0])

    print("\n--- INFORMACION TEMPORAL ---")
    for key in ["DATE-OBS", "DATE-END", "MJD-OBS"]:
        print(key, ":", header.get(key, "No disponible"))

    print("\n--- COBERTURA ---")
    print("Pixeles con observaciones:", np.sum(hits > 0))
    print("Pixeles marcados:", np.sum(flags != 0))

    print("\n--- CANALES ESPECTRALES ---")
    channels = Table(hdul["SPECTRAL_CHANNELS"].data)
    print(channels[:5])

    print("\n--- WCS ESPECTRAL ---")
    wave = Table(hdul["WCS-WAVE"].data)
    print("Columnas:", wave.colnames)