
from pathlib import Path
import warnings
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.wcs import NoConvergence
import astropy.units as u

files = [
    Path(
        "SPHERExLVFSurveyData/"
        "level2_2025W38_1A_0596_1D6_spx_l2b-v27-2026-237.fits"
    ),
    Path(
        "SPHERExLVFSurveyData-1/"
        "level2_2026W39_2A_0324_4D6_spx_l2b-v27-2026-271.fits"
    ),
]

with fits.open(files[0], memmap=True) as a, \
     fits.open(files[1], memmap=True) as b:

    # WCS espacial
    wa = WCS(a["IMAGE"].header).celestial
    wb = WCS(b["IMAGE"].header).celestial

    # WCS espectral: aproximación exploratoria
    sa = WCS(a["IMAGE"].header, fobj=a, key="W")
    sb = WCS(b["IMAGE"].header, fobj=b, key="W")
    sa.sip = None
    sb.sip = None

    h1, w1 = a["IMAGE"].data.shape
    h2, w2 = b["IMAGE"].data.shape

    # Buscar una región segura dentro de los dos detectores
    margin = 30

    gx, gy = np.meshgrid(
        np.linspace(margin, w1 - margin - 1, 65),
        np.linspace(margin, h1 - margin - 1, 65),
    )

    ra, dec = wa.pixel_to_world_values(gx, gy)

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=".*WCS.all_world2pix.*"
        )
        try:
            xb, yb = wb.world_to_pixel_values(ra, dec)
        except NoConvergence as exc:
            xy = np.asarray(exc.best_solution)
            xb, yb = xy[..., 0], xy[..., 1]

    valid = (
        np.isfinite(xb)
        & np.isfinite(yb)
        & (xb >= margin)
        & (xb < w2 - margin)
        & (yb >= margin)
        & (yb < h2 - margin)
    )

    print("Puntos con solape espacial:", int(valid.sum()))

    if not valid.any():
        raise SystemExit(
            "No hay campo común útil en este muestreo."
        )

    x1, y1 = gx[valid], gy[valid]
    x2, y2 = xb[valid], yb[valid]
    r, d = ra[valid], dec[valid]

    # Verificar que las transformaciones WCS son consistentes
    rr, dd = wb.pixel_to_world_values(x2, y2)
    back_x, back_y = wa.world_to_pixel_values(rr, dd)

    stable = (
        np.isfinite(back_x)
        & np.isfinite(back_y)
        & (np.hypot(back_x - x1, back_y - y1) < 0.5)
    )

    x1, y1, x2, y2, r, d = [
        z[stable]
        for z in (x1, y1, x2, y2, r, d)
    ]

    if x1.size == 0:
        raise SystemExit(
            "El solape no superó la prueba WCS inversa."
        )

    # Revisar píxeles y varianza en ambas exposiciones
    i1, j1 = np.rint(x1).astype(int), np.rint(y1).astype(int)
    i2, j2 = np.rint(x2).astype(int), np.rint(y2).astype(int)

    usable = (
        np.isfinite(a["IMAGE"].data[j1, i1])
        & np.isfinite(b["IMAGE"].data[j2, i2])
        & np.isfinite(a["VARIANCE"].data[j1, i1])
        & np.isfinite(b["VARIANCE"].data[j2, i2])
        & (a["VARIANCE"].data[j1, i1] > 0)
        & (b["VARIANCE"].data[j2, i2] > 0)
        & (a["FLAGS"].data[j1, i1] == 0)
        & (b["FLAGS"].data[j2, i2] == 0)
    )

    x1, y1, x2, y2, r, d = [
        z[usable]
        for z in (x1, y1, x2, y2, r, d)
    ]

    print(
        "Puntos con FLAGS=0 y varianza válida:",
        len(r)
    )

    if len(r) == 0:
        raise SystemExit(
            "No hay puntos que pasen estos filtros conservadores."
        )

    # Calcular longitud de onda aproximada
    l1, bw1 = sa.pixel_to_world(x1, y1)
    l2, bw2 = sb.pixel_to_world(x2, y2)

    l1 = l1.to_value(u.um)
    l2 = l2.to_value(u.um)
    bw1 = bw1.to_value(u.um)
    bw2 = bw2.to_value(u.um)

    spectral_valid = (
        np.isfinite(l1)
        & np.isfinite(l2)
        & np.isfinite(bw1)
        & np.isfinite(bw2)
        & (bw1 > 0)
        & (bw2 > 0)
    )

    if not spectral_valid.any():
        raise SystemExit(
            "No se pudieron calcular bandas válidas."
        )

    idx = np.flatnonzero(spectral_valid)

    # Desajuste entre longitudes de onda relativo al ancho
    score = (
        np.abs(l1[idx] - l2[idx])
        / ((bw1[idx] + bw2[idx]) / 2)
    )

    idx = idx[np.argsort(score)]

    print("\nMEJORES REGIONES PARA COMPARAR:")

    for k in idx[:3]:
        ratio = (
            abs(l1[k] - l2[k])
            / ((bw1[k] + bw2[k]) / 2)
        )

        print(f"\nRA={r[k]:.7f}  Dec={d[k]:.7f}")

        print(
            f"2025: longitud={l1[k]:.5f} um, "
            f"ancho={bw1[k]:.5f} um"
        )

        print(
            f"2026: longitud={l2[k]:.5f} um, "
            f"ancho={bw2[k]:.5f} um"
        )

        print(f"Desajuste relativo: {ratio:.2f}")

    best = idx[0]

    ratio = (
        abs(l1[best] - l2[best])
        / ((bw1[best] + bw2[best]) / 2)
    )

    print("\nEVALUACIÓN PRELIMINAR:")

    if ratio < 0.25:
        print(
            "Existe una zona espectral prometedora. "
            "Falta validar CWAVE/CBAND, PSF y calidad local."
        )
    else:
        print(
            "Las longitudes de onda difieren demasiado "
            "para una comparación directa en este muestreo."
        )
