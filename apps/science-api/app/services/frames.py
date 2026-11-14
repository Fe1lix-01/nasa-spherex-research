
"""
Servicio de extracción de metadatos astronómicos.

Se encarga de leer los archivos FITS, interpretar su información WCS
y construir los metadatos que posteriormente entrega la API.
"""

# math permite comprobar que los valores astronómicos sean finitos.
import math

# re permite identificar el detector SPHEREx en el nombre del archivo.
import re

# Path permite trabajar con rutas del sistema de archivos.
from pathlib import Path

# fits permite abrir y leer archivos astronómicos FITS.
from astropy.io import fits

# WCS interpreta la información de coordenadas celestes del encabezado.
from astropy.wcs import WCS

# proj_plane_pixel_scales calcula la escala angular de los píxeles.
from astropy.wcs.utils import proj_plane_pixel_scales

# Importamos la ruta centralizada del directorio de archivos FITS.
from app.core.paths import FITS_DIR


# Expresión regular que identifica los detectores D1 a D6
# dentro del nombre de cada archivo FITS.
DETECTOR_PATTERN = re.compile(r"_D([1-6])_")


class FrameMetadataError(ValueError):
    """
    Error que indica que un archivo FITS no contiene dimensiones,
    coordenadas WCS o metadatos astronómicos válidos.
    """
    pass


def extract_frame_metadata(path: Path) -> dict:
    """
    Extrae los metadatos astronómicos de un archivo FITS.

    Lee las dimensiones de la imagen y utiliza WCS para calcular
    el centro celeste, la escala angular y el campo de visión.

    Args:
        path: Ruta del archivo FITS que se va a procesar.

    Returns:
        Diccionario con los metadatos del frame.

    Raises:
        FrameMetadataError: Si el archivo no contiene información válida.
    """

    # Identificamos el detector a partir del nombre del archivo.
    detector_match = DETECTOR_PATTERN.search(path.name)

    # Sin un detector D1-D6 no podemos identificar correctamente el frame.
    if detector_match is None:
        raise FrameMetadataError(
            f"No se pudo identificar el detector en {path.name}"
        )

    try:
        # Abrimos el FITS sin mantener un mapeo de memoria del archivo.
        with fits.open(path, memmap=False) as hdul:

            # Utilizamos la información de la unidad primaria del FITS.
            primary_hdu = hdul[0]

            # Obtenemos los datos científicos y su encabezado.
            data = primary_hdu.data
            header = primary_hdu.header

            # Comprobamos que el FITS contenga una imagen.
            if data is None:
                raise FrameMetadataError(
                    f"El archivo {path.name} no contiene datos de imagen"
                )

            # El servicio espera imágenes bidimensionales, no cubos de datos.
            if data.ndim != 2:
                raise FrameMetadataError(
                    f"El archivo {path.name} no contiene una imagen 2D"
                )

            # Extraemos las dimensiones reales de la imagen.
            height, width = data.shape

            # Evitamos procesar imágenes sin dimensiones válidas.
            if width <= 0 or height <= 0:
                raise FrameMetadataError(
                    f"El archivo {path.name} tiene dimensiones inválidas"
                )

            # Construimos el objeto WCS utilizando el encabezado FITS.
            wcs = WCS(header)

            # Verificamos que el encabezado contenga coordenadas celestes.
            if not wcs.has_celestial:
                raise FrameMetadataError(
                    f"El archivo {path.name} no contiene información WCS celestial"
                )

            # Conservamos únicamente los componentes celestes del WCS.
            celestial_wcs = wcs.celestial

            # Obtenemos los tipos de coordenadas utilizados por el FITS.
            ctype1 = celestial_wcs.wcs.ctype[0].upper()
            ctype2 = celestial_wcs.wcs.ctype[1].upper()

            # El contrato actual utiliza ascensión recta y declinación.
            if not ctype1.startswith("RA") or not ctype2.startswith("DEC"):
                raise FrameMetadataError(
                    f"El WCS de {path.name} no utiliza coordenadas RA/DEC"
                )

            # Calculamos el centro geométrico de la imagen.
            # Se resta 1 porque los índices de píxel comienzan en cero.
            center_x = (width - 1) / 2
            center_y = (height - 1) / 2

            # Convertimos el centro de píxeles a coordenadas celestes.
            center = celestial_wcs.pixel_to_world(center_x, center_y)

            # Extraemos ascensión recta y declinación en grados.
            center_ra_deg = float(center.ra.deg) % 360
            center_dec_deg = float(center.dec.deg)

            # Calculamos la escala angular de cada eje en grados por píxel.
            pixel_scales = proj_plane_pixel_scales(celestial_wcs)

            # Convertimos las escalas a segundos de arco por píxel.
            pixel_scale_x_arcsec = abs(float(pixel_scales[0])) * 3600
            pixel_scale_y_arcsec = abs(float(pixel_scales[1])) * 3600

            # Calculamos el campo de visión utilizando las dimensiones reales.
            fov_x_deg = pixel_scale_x_arcsec * width / 3600
            fov_y_deg = pixel_scale_y_arcsec * height / 3600

            # Comprobamos que los resultados no contengan NaN o infinito.
            numeric_values = [
                center_ra_deg,
                center_dec_deg,
                pixel_scale_x_arcsec,
                pixel_scale_y_arcsec,
                fov_x_deg,
                fov_y_deg,
            ]

            if not all(math.isfinite(value) for value in numeric_values):
                raise FrameMetadataError(
                    f"El archivo {path.name} produjo metadatos no finitos"
                )

            # Recuperamos el sistema de referencia declarado en el WCS.
            # Para coordenadas RA/DEC, ICRS es el valor predeterminado.
            coordinate_system = celestial_wcs.wcs.radesys or "ICRS"

            # Extraemos la proyección del primer eje del WCS.
            # Por ejemplo, RA---TAN produce la proyección TAN.
            projection = ctype1.split("-")[-1]

            # Construimos el diccionario con el contrato de metadatos.
            return {
                "id": path.name,
                "detector": f"D{detector_match.group(1)}",
                "filename": path.name,
                "format": "FITS",
                "width": int(width),
                "height": int(height),
                "center_ra_deg": center_ra_deg,
                "center_dec_deg": center_dec_deg,
                "pixel_scale_x_arcsec": pixel_scale_x_arcsec,
                "pixel_scale_y_arcsec": pixel_scale_y_arcsec,
                "fov_x_deg": fov_x_deg,
                "fov_y_deg": fov_y_deg,
                "coordinate_system": coordinate_system,
                "projection": projection,
            }

    except FrameMetadataError:
        # Conservamos los errores de validación que generamos explícitamente.
        raise

    except Exception as exc:
        # Convertimos los errores de lectura o interpretación de Astropy
        # en un error controlado que pueda manejar el router.
        raise FrameMetadataError(
            f"No fue posible procesar los metadatos de {path.name}: {exc}"
        ) from exc


def list_frames() -> list[dict]:
    """
    Busca los archivos FITS disponibles y extrae sus metadatos.

    Returns:
        Lista de diccionarios con los metadatos de cada frame.

    Raises:
        FileNotFoundError: Si el directorio de FITS no está disponible.
        FrameMetadataError: Si alguno de los archivos no puede procesarse.
    """

    # Comprobamos que el directorio centralizado exista.
    if not FITS_DIR.is_dir():
        raise FileNotFoundError(
            f"No existe el directorio de imágenes FITS: {FITS_DIR}"
        )

    # Recuperamos los FITS y mantenemos un orden determinista.
    fits_files = sorted(FITS_DIR.glob("*.fits"))

    # Procesamos cada archivo y construimos la lista de metadatos.
    frames = [
        extract_frame_metadata(path)
        for path in fits_files
    ]

    return frames
