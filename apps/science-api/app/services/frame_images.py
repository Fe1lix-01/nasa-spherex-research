
"""
Servicio de conversión de imágenes astronómicas FITS a PNG.

Genera imágenes PNG para visualización sin modificar los archivos
FITS originales ni alterar sus datos científicos.
"""

# BytesIO permite generar el PNG en memoria, sin crear archivos temporales.
from io import BytesIO

# Path permite manejar rutas del sistema de archivos.
from pathlib import Path

# NumPy permite normalizar los valores numéricos de la imagen.
import numpy as np

# Astropy permite abrir y leer archivos FITS.
from astropy.io import fits

# Pillow permite codificar la matriz de píxeles como PNG.
from PIL import Image

# Importamos la ubicación centralizada de los archivos FITS.
from app.core.paths import FITS_DIR


class FrameImageNotFoundError(LookupError):
    """Indica que el frame solicitado no existe."""


class FrameImageError(ValueError):
    """Indica que no fue posible procesar la imagen FITS."""


def _resolve_frame_path(frame_id: str) -> Path:
    """
    Busca un FITS por su nombre exacto dentro del directorio autorizado.

    No acepta rutas proporcionadas por el usuario. Esto evita que el
    endpoint pueda acceder a archivos fuera del directorio de imágenes.
    """

    # Comprobamos que el directorio de imágenes esté disponible.
    if not FITS_DIR.is_dir():
        raise FileNotFoundError(
            f"No existe el directorio de imágenes FITS: {FITS_DIR}"
        )

    # Buscamos únicamente archivos FITS cuyo nombre coincida exactamente.
    frame_path = next(
        (
            path
            for path in FITS_DIR.glob("*.fits")
            if path.name == frame_id
        ),
        None,
    )

    # Si no encontramos coincidencias, informamos que el frame no existe.
    if frame_path is None:
        raise FrameImageNotFoundError(
            f"No existe el frame solicitado: {frame_id}"
        )

    return frame_path


def _normalize_image(data: np.ndarray) -> np.ndarray:
    """
    Convierte los valores científicos a intensidades de 8 bits.

    Utiliza los percentiles 1 y 99 para mejorar el contraste visual.
    Los valores NaN e infinitos se representan como píxeles negros.
    """

    # Convertimos los datos a números de punto flotante.
    image_data = np.asarray(data, dtype=np.float64)

    # El servicio solamente admite imágenes bidimensionales.
    if image_data.ndim != 2 or image_data.size == 0:
        raise FrameImageError(
            "El archivo FITS no contiene una imagen 2D válida"
        )

    # Identificamos los píxeles que contienen valores numéricos válidos.
    finite_mask = np.isfinite(image_data)

    # No podemos generar una imagen útil si todos los píxeles son inválidos.
    if not np.any(finite_mask):
        raise FrameImageError(
            "La imagen FITS no contiene valores numéricos válidos"
        )

    # Extraemos únicamente los valores finitos para calcular el contraste.
    finite_values = image_data[finite_mask]

    # Calculamos los límites de intensidad para reducir el efecto de valores
    # extremos sin modificar los datos originales del archivo FITS.
    lower, upper = np.percentile(finite_values, [1, 99])

    # Comprobamos que los límites calculados sean válidos.
    if not np.isfinite(lower) or not np.isfinite(upper):
        raise FrameImageError(
            "No fue posible calcular el rango de intensidad de la imagen"
        )

    # Inicializamos los píxeles inválidos en negro.
    pixels = np.zeros(image_data.shape, dtype=np.uint8)

    # Si todos los valores son iguales, representamos los píxeles válidos
    # con un gris medio para evitar una división entre cero.
    if upper <= lower:
        pixels[finite_mask] = 127
        return pixels

    # Limitamos los valores al rango de contraste calculado.
    clipped_values = np.clip(finite_values, lower, upper)

    # Escalamos los valores válidos al intervalo de 0 a 255.
    normalized_values = (
        (clipped_values - lower) / (upper - lower)
    ) * 255.0

    # Convertimos las intensidades a enteros de 8 bits.
    pixels[finite_mask] = np.rint(normalized_values).astype(np.uint8)

    return pixels

def render_image_png(data: np.ndarray) -> bytes:
    """Convierte una imagen científica 2D en un PNG de visualización."""
    pixels = _normalize_image(data)

    output = BytesIO()
    Image.fromarray(pixels).save(output, format="PNG")

    return output.getvalue()

def render_frame_png(frame_id: str) -> bytes:
    """
    Lee un FITS y devuelve su representación PNG en memoria.

    Args:
        frame_id: Nombre exacto del archivo FITS.

    Returns:
        Contenido binario de la imagen PNG.

    Raises:
        FileNotFoundError: Si el directorio FITS no está disponible.
        FrameImageNotFoundError: Si el frame no existe.
        FrameImageError: Si el FITS no puede convertirse.
    """

    # Resolvemos el nombre del archivo dentro del directorio autorizado.
    frame_path = _resolve_frame_path(frame_id)

    try:
        # Abrimos el archivo sin mantener un mapeo de memoria.
        with fits.open(frame_path, memmap=False) as hdul:

            # Utilizamos los datos de la unidad primaria del FITS.
            data = hdul[0].data

            # Comprobamos que el archivo contenga datos de imagen.
            if data is None:
                raise FrameImageError(
                    "El archivo FITS no contiene datos de imagen"
                )
            return render_image_png(data)

    except FrameImageError:
        # Conservamos los errores de validación generados por el servicio.
        raise

    except Exception as exc:
        # Convertimos errores de lectura o codificación en errores controlados.
        raise FrameImageError(
            f"No fue posible convertir el frame {frame_id} a PNG"
        ) from exc
