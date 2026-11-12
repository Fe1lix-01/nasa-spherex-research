import sys
from pathlib import Path

from astropy.utils.data import download_file


# Localiza la raíz del proyecto desde la carpeta de esta práctica.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Permite importar el paquete app del backend al ejecutar esta práctica.
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "science-api"))

from app.services.m101 import generar_figura_m101


if __name__ == "__main__":
    url = (
        "https://irsa.ipac.caltech.edu/data/demos/"
        "notebooks/spherex/M101_irsa.fits"
    )

    # Reutiliza el FITS guardado en la caché de Astropy.
    archivo = Path(download_file(url, cache=True))

    ruta_salida = (
        Path(__file__).resolve().parent
        / "outputs"
        / "11_m101_canal_63.png"
    )

    generar_figura_m101(
        archivo=archivo,
        ruta_salida=ruta_salida,
        canal=63,
    )

    print("\nFITS utilizado:", archivo)
    print("Imagen guardada en:", ruta_salida)