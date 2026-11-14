
from pathlib import Path
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

archivo_2025 = Path(
    "SPHERExLVFSurveyData/"
    "level2_2025W38_1A_0596_1D6_spx_l2b-v27-2026-237.fits"
)

archivo_2026 = Path(
    "SPHERExLVFSurveyData-1/"
    "level2_2026W39_2A_0324_4D6_spx_l2b-v27-2026-271.fits"
)

with fits.open(archivo_2025, memmap=True) as a, \
     fits.open(archivo_2026, memmap=True) as b:

    img1 = a["IMAGE"].data
    img2 = b["IMAGE"].data

    w1 = WCS(a["IMAGE"].header).celestial
    w2 = WCS(b["IMAGE"].header).celestial

    # ¿Barnard aparece en los FITS completos?
    target_ra = 269.4463
    target_dec = 4.7682

    for nombre, w, img in [
        ("2025", w1, img1),
        ("2026", w2, img2),
    ]:
        x, y = w.world_to_pixel_values(
            target_ra, target_dec
        )

        dentro = (
            np.isfinite(x)
            and np.isfinite(y)
            and 0 <= x < img.shape[1]
            and 0 <= y < img.shape[0]
        )

        print(f"Barnard dentro de {nombre}: {dentro}")

    # Muestrear posiciones de la primera imagen
    ys, xs = np.meshgrid(
        np.linspace(0, img1.shape[0] - 1, 60),
        np.linspace(0, img1.shape[1] - 1, 60),
        indexing="ij"
    )

    ra, dec = w1.pixel_to_world_values(xs, ys)
    x2, y2 = w2.world_to_pixel_values(ra, dec)

    # Margen para que quepa un recorte
    margin = 25

    common = (
        np.isfinite(x2)
        & np.isfinite(y2)
        & (xs >= margin)
        & (ys >= margin)
        & (xs < img1.shape[1] - margin)
        & (ys < img1.shape[0] - margin)
        & (x2 >= margin)
        & (y2 >= margin)
        & (x2 < img2.shape[1] - margin)
        & (y2 < img2.shape[0] - margin)
    )

    print("\nPuntos muestreados comunes:", common.sum())

    if common.any():
        print("Posible región común:")
        print("RA:", float(np.median(ra[common])))
        print("Dec:", float(np.median(dec[common])))
        print(
            "Existe una región compartida aproximada. "
            "Falta comprobar su banda espectral."
        )
    else:
        print(
            "No se encontró una región compartida "
            "en este muestreo con margen de seguridad."
        )
