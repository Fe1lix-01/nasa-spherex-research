
"""
Esquemas de validación para los frames astronómicos.

Estos modelos definen la estructura de los datos que
la API entrega al frontend.
"""

# Literal permite limitar un campo a un conjunto específico de valores.
from typing import Literal

# BaseModel permite definir modelos de datos validados por Pydantic.
# Field permite establecer restricciones para los atributos.
from pydantic import BaseModel, Field


class FrameMetadata(BaseModel):
    """
    Representa los metadatos de una imagen FITS.

    Incluye información del detector, dimensiones de la imagen,
    coordenadas celestes, escala de píxel y campo de visión.
    """

    # Identificador único basado en el nombre del archivo FITS.
    id: str

    # Detector SPHEREx al que pertenece la observación.
    detector: Literal["D1", "D2", "D3", "D4", "D5", "D6"]

    # Nombre original del archivo almacenado en disco.
    filename: str

    # Formato del archivo científico original.
    format: Literal["FITS"]

    # Dimensiones de la imagen expresadas en píxeles.
    width: int = Field(gt=0)
    height: int = Field(gt=0)

    # Coordenadas del centro de la imagen en grados.
    center_ra_deg: float = Field(ge=0, lt=360)
    center_dec_deg: float = Field(ge=-90, le=90)

    # Escala angular de cada píxel en los ejes X e Y.
    pixel_scale_x_arcsec: float = Field(gt=0)
    pixel_scale_y_arcsec: float = Field(gt=0)

    # Campo de visión de la imagen en grados.
    fov_x_deg: float = Field(gt=0)
    fov_y_deg: float = Field(gt=0)

    # Sistema de coordenadas celestes utilizado por el FITS.
    coordinate_system: str

    # Proyección geométrica utilizada por el WCS.
    projection: str


class FramesResponse(BaseModel):
    """
    Representa la respuesta del endpoint GET /api/v1/frames.

    Contiene el número total de frames y la lista de sus metadatos.
    """

    # Cantidad total de frames encontrados.
    total: int = Field(ge=0)

    # Lista de frames que cumplen con el esquema FrameMetadata.
    frames: list[FrameMetadata]
