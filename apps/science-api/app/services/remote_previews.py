from io import BytesIO

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from app.clients.irsa import IrsaResponseError
from app.clients.irsa_cutouts import download_irsa_cutout
from app.services.frame_images import render_image_png
from app.services.objects import get_object


class RemotePreviewNotFoundError(LookupError):
    """El objeto o producto solicitado no está registrado."""


def render_cutout_png(content: bytes, ra: float, dec: float) -> bytes:
    """Valida un recorte FITS y genera su PNG de visualización."""
    try:
        with fits.open(BytesIO(content), memmap=False) as hdul:
            if "IMAGE" not in hdul:
                raise ValueError("El recorte carece de IMAGE.")

            hdu = hdul["IMAGE"]
            data = hdu.data

            if data is None or data.ndim != 2 or data.size == 0:
                raise ValueError("IMAGE debe contener una imagen 2D.")

            wcs = WCS(hdu.header, fobj=hdul).celestial

            if not wcs.has_celestial:
                raise ValueError("El recorte carece de WCS celestial.")

            x, y = wcs.world_to_pixel_values(ra, dec)
            height, width = data.shape

            if not (
                np.isfinite(x)
                and np.isfinite(y)
                and -0.5 <= x < width - 0.5
                and -0.5 <= y < height - 0.5
            ):
                raise ValueError(
                    "La posición solicitada queda fuera del recorte."
                )

            return render_image_png(data)

    except Exception as error:
        raise IrsaResponseError(
            "No fue posible interpretar el recorte FITS de IRSA."
        ) from error


def render_remote_observation_png(
    object_id: str,
    product_id: str,
) -> bytes:
    """Genera una previsualización de un producto remoto del catálogo."""
    target = get_object(object_id)

    if target is None:
        raise RemotePreviewNotFoundError()

    observation = next(
        (
            item
            for item in target.get("remote_observations", [])
            if item["product_id"] == product_id
        ),
        None,
    )

    if observation is None:
        raise RemotePreviewNotFoundError()

    query = target.get("remote_query")

    if query is None:
        raise IrsaResponseError(
            "El registro carece de la posición de consulta."
        )

    content = download_irsa_cutout(
        url=observation["access_url"],
        ra=query["ra"],
        dec=query["dec"],
    )

    return render_cutout_png(
        content,
        ra=query["ra"],
        dec=query["dec"],
    )