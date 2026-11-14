
"""
MORLEY FRONTIER
RA/Dec -> WCS -> ZOGY -> Model Comparator

Prueba:
    python morley_wcs_zogy_comparator.py --demo

Dependencias:
    pip install numpy scipy astropy matplotlib

IMPORTANTE:
- Esta prueba utiliza imágenes sintéticas.
- No incluye paralaje de SPHEREx.
- ZOGY supone ruido gaussiano blanco.
- No implementa S_corr (ecuación 25).
- No procesa todavía FITS reales directamente.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.ndimage import shift as nd_shift
from scipy.optimize import minimize, nnls


# ==========================================================
# 1. DATOS DE REFERENCIA DE BARNARD
# ==========================================================

# Coordenadas de ejemplo cercanas a 2025.
# Sustituir por astrometría catalogada verificada
# cuando se trabaje con observaciones reales.

BARNARD = {
    "ra_deg": 269.4463,
    "dec_deg": 4.7682,
    "reference_mjd": 60970.0,
    "pm_ra_cosdec_masyr": -802.803,
    "pm_dec_masyr": 10362.5,
}


# ==========================================================
# 2. ASTROMETRÍA: RA/DEC + TIEMPO
# ==========================================================

def propagate_pm(
    ra_deg,
    dec_deg,
    mjd0,
    mjd,
    pmra,
    pmdec,
):
    """
    Propaga RA/Dec mediante movimiento propio.

    No incluye paralaje, velocidad radial ni
    movimiento del observador.
    """

    dt = (float(mjd) - float(mjd0)) / 365.25

    cosdec = np.cos(np.deg2rad(dec_deg))

    if abs(cosdec) < 1e-7:
        raise ValueError(
            "Cerca de los polos, usar "
            "SkyCoord.apply_space_motion"
        )

    ra = (
        float(ra_deg)
        + float(pmra) * dt / (3.6e6 * cosdec)
    ) % 360

    dec = (
        float(dec_deg)
        + float(pmdec) * dt / 3.6e6
    )

    return ra, dec


# ==========================================================
# 3. WCS: COORDENADAS CELESTES -> PÍXELES
# ==========================================================

class DemoTANWCS:
    """
    Proyección TAN simplificada.

    Alternativa de demostración cuando Astropy
    no está disponible.

    No sustituye el WCS real de un FITS.
    """

    def __init__(
        self,
        ra0,
        dec0,
        x0,
        y0,
        arcsec_per_pixel,
    ):
        self.ra0 = np.deg2rad(ra0)
        self.dec0 = np.deg2rad(dec0)
        self.x0 = float(x0)
        self.y0 = float(y0)
        self.scale = float(arcsec_per_pixel)

    def world_to_pixel_values(self, ra, dec):

        alpha, delta = np.deg2rad([ra, dec])

        da = np.arctan2(
            np.sin(alpha - self.ra0),
            np.cos(alpha - self.ra0),
        )

        sin0 = np.sin(self.dec0)
        cos0 = np.cos(self.dec0)

        sind = np.sin(delta)
        cosd = np.cos(delta)

        den = (
            sin0 * sind
            + cos0 * cosd * np.cos(da)
        )

        if den <= 0:
            raise ValueError(
                "Fuera del hemisferio TAN"
            )

        xi = cosd * np.sin(da) / den

        eta = (
            cos0 * sind
            - sin0 * cosd * np.cos(da)
        ) / den

        x = (
            self.x0
            - np.rad2deg(xi) * 3600 / self.scale
        )

        y = (
            self.y0
            + np.rad2deg(eta) * 3600 / self.scale
        )

        return x, y


def make_wcs(
    ra0,
    dec0,
    size,
    arcsec_per_pixel,
):
    """
    Construye WCS TAN.

    Utiliza Astropy si está instalado.
    """

    try:
        from astropy.wcs import WCS

        w = WCS(naxis=2)

        w.wcs.crpix = [
            size / 2 + 0.5,
            size / 2 + 0.5,
        ]

        w.wcs.cdelt = [
            -arcsec_per_pixel / 3600,
            arcsec_per_pixel / 3600,
        ]

        w.wcs.crval = [ra0, dec0]

        w.wcs.ctype = [
            "RA---TAN",
            "DEC--TAN",
        ]

        return w, "astropy_TAN"

    except ImportError:

        w = DemoTANWCS(
            ra0,
            dec0,
            size / 2 - 0.5,
            size / 2 - 0.5,
            arcsec_per_pixel,
        )

        return w, "demo_TAN_fallback"


def world_to_pixel(wcs, ra, dec):

    x, y = wcs.world_to_pixel_values(
        ra,
        dec,
    )

    return float(x), float(y)


# ==========================================================
# 4. GENERACIÓN DE IMÁGENES SINTÉTICAS
# ==========================================================

def gaussian_psf(
    size=21,
    width=1.55,
):
    """
    Genera una PSF gaussiana normalizada.
    """

    if size % 2 != 1:
        raise ValueError(
            "El tamaño PSF debe ser impar"
        )

    y, x = np.indices(
        (size, size),
        dtype=float,
    )

    p = np.exp(
        -(
            (x - size // 2) ** 2
            + (y - size // 2) ** 2
        ) / (2 * width**2)
    )

    return p / p.sum()


def stamp_source(
    shape,
    psf,
    x,
    y,
    flux,
):
    """
    Coloca una estrella sintética en una
    posición subpíxel.
    """

    p = np.asarray(psf, dtype=float)

    canvas = np.zeros(
        shape,
        dtype=float,
    )

    cy = shape[0] // 2 - p.shape[0] // 2
    cx = shape[1] // 2 - p.shape[1] // 2

    canvas[
        cy:cy + p.shape[0],
        cx:cx + p.shape[1],
    ] = p

    shifted = nd_shift(
        canvas,
        shift=(
            y - shape[0] // 2,
            x - shape[1] // 2,
        ),
        order=3,
        mode="constant",
        cval=0.0,
        prefilter=True,
    )

    return flux * shifted


# ==========================================================
# 5. ZOGY: PROPER IMAGE SUBTRACTION
# ==========================================================

def psf_fft(psf, shape):

    p = np.asarray(psf, dtype=float)

    if (
        p.ndim != 2
        or any(
            q > s
            for q, s in zip(p.shape, shape)
        )
    ):
        raise ValueError(
            "La PSF 2D debe caber en la imagen"
        )

    if (
        not np.isfinite(p).all()
        or p.sum() <= 0
    ):
        raise ValueError("PSF inválida")

    p = p / p.sum()

    canvas = np.zeros(shape)

    y = shape[0] // 2 - p.shape[0] // 2
    x = shape[1] // 2 - p.shape[1] // 2

    canvas[
        y:y + p.shape[0],
        x:x + p.shape[1],
    ] = p

    return np.fft.fft2(
        np.fft.ifftshift(canvas)
    )


@dataclass
class ZOGY:
    difference: np.ndarray
    psf_d: np.ndarray
    significance: np.ndarray
    f_d: float


def zogy(
    reference,
    new,
    psf_r,
    psf_n,
    sigma_r,
    sigma_n,
    fr=1.0,
    fn=1.0,
):
    """
    ZOGY idealizado, ecuaciones 13–16.

    Requisitos:
    - Imágenes alineadas.
    - Misma forma.
    - Banda espectral compatible.
    - Calibración fotométrica consistente.
    - Ruido gaussiano homogéneo.
    """

    ref = np.asarray(reference, float)
    nxt = np.asarray(new, float)

    if (
        ref.ndim != 2
        or ref.shape != nxt.shape
        or min(ref.shape) < 16
    ):
        raise ValueError(
            "Las imágenes deben tener "
            "el mismo tamaño 2D"
        )

    if (
        not np.isfinite(ref).all()
        or not np.isfinite(nxt).all()
    ):
        raise ValueError(
            "Corregir máscara/NaN antes de ZOGY"
        )

    if min(
        sigma_r,
        sigma_n,
        fr,
        fn,
    ) <= 0:
        raise ValueError(
            "Sigmas y factores fotométricos "
            "deben ser positivos"
        )

    pr = psf_fft(psf_r, ref.shape)
    pn = psf_fft(psf_n, ref.shape)

    # Denominador de ZOGY
    den = np.sqrt(
        sigma_n**2 * fr**2 * np.abs(pr)**2
        +
        sigma_r**2 * fn**2 * np.abs(pn)**2
    )

    good = den > 1e-12 * den.max()

    dh = np.zeros(
        ref.shape,
        dtype=complex,
    )

    numerator = (
        fr * pr * np.fft.fft2(nxt)
        -
        fn * pn * np.fft.fft2(ref)
    )

    dh[good] = (
        numerator[good] / den[good]
    )

    # Escala fotométrica de diferencia
    fd = (
        fr * fn
        / np.hypot(
            sigma_n * fr,
            sigma_r * fn,
        )
    )

    # PSF efectiva de diferencia
    pdh = np.zeros(
        ref.shape,
        dtype=complex,
    )

    pdh[good] = (
        fr * fn * pr[good] * pn[good]
        / (fd * den[good])
    )

    pd = np.fft.fftshift(
        np.fft.ifft2(pdh).real
    )

    norm = np.linalg.norm(pd)

    if norm < 1e-12:
        raise ValueError(
            "PSF de diferencia degenerada"
        )

    # Significancia ideal
    snr = (
        np.fft.ifft2(
            dh * np.conj(pdh)
        ).real
        / norm
    )

    return ZOGY(
        difference=np.fft.ifft2(dh).real,
        psf_d=pd,
        significance=snr,
        f_d=float(fd),
    )


# ==========================================================
# 6. MORLEY MODEL COMPARATOR
# ==========================================================

LABELS = {
    "H0": "sin_cambio",
    "H1": "variabilidad",
    "H2": "movimiento",
    "H3": "movimiento_y_variabilidad",
}


def compare_models(
    difference,
    psf_d,
    center_yx,
    max_shift=3.5,
    radius=12,
):
    """
    Compara:

    H0: ausencia de cambio
    H1: variación de brillo
    H2: desplazamiento con flujo constante
    H3: desplazamiento y variación de brillo

    Selección mediante BIC experimental.
    """

    d = np.asarray(difference, float)
    pd = np.asarray(psf_d, float)

    if d.ndim != 2 or d.shape != pd.shape:
        raise ValueError(
            "D y P_D deben tener el mismo tamaño"
        )

    cy, cx = map(float, center_yx)

    iy = round(cy)
    ix = round(cx)

    y0 = iy - radius
    y1 = iy + radius + 1

    x0 = ix - radius
    x1 = ix + radius + 1

    if (
        min(y0, x0) < 0
        or y1 > d.shape[0]
        or x1 > d.shape[1]
    ):
        raise ValueError(
            "Región demasiado cerca del borde"
        )

    obs = d[
        y0:y1,
        x0:x1,
    ].ravel()

    n = obs.size

    def template(dx, dy):

        t = nd_shift(
            pd,
            (
                cy - pd.shape[0] // 2 + dy,
                cx - pd.shape[1] // 2 + dx,
            ),
            order=3,
            mode="constant",
            cval=0.0,
            prefilter=True,
        )

        return t[
            y0:y1,
            x0:x1,
        ].ravel()

    p0 = template(0.0, 0.0)

    # H0: sin cambio
    chi0 = obs @ obs

    # H1: variabilidad
    amp1 = (obs @ p0) / (p0 @ p0)

    chi1 = np.sum(
        (obs - amp1 * p0) ** 2
    )

    # H2 y H3
    def fit(offset, model):

        dx, dy = offset

        pp = template(dx, dy)

        if model == "H2":

            basis = pp - p0

            amp = max(
                0.0,
                (obs @ basis)
                / max(1e-14, basis @ basis),
            )

            residual = obs - amp * basis

            return (
                np.sum(residual**2),
                [float(amp)],
            )

        # H3: amplitudes independientes
        matrix = np.column_stack(
            (pp, -p0)
        )

        amps, _ = nnls(
            matrix,
            obs,
        )

        residual = obs - matrix @ amps

        return (
            np.sum(residual**2),
            amps.tolist(),
        )

    def optimize(model):

        limit = float(max_shift)

        best = (
            float("inf"),
            None,
            None,
        )

        for sx in np.linspace(
            -limit, limit, 5
        ):
            for sy in np.linspace(
                -limit, limit, 5
            ):

                result = minimize(
                    lambda z: fit(z, model)[0],
                    (sx, sy),
                    method="L-BFGS-B",
                    bounds=[
                        (-limit, limit),
                        (-limit, limit),
                    ],
                    options={"maxiter": 60},
                )

                chi, amps = fit(
                    result.x,
                    model,
                )

                if chi < best[0]:
                    best = (
                        float(chi),
                        result.x.tolist(),
                        amps,
                    )

        return best

    chi2, shift2, amps2 = optimize("H2")
    chi3, shift3, amps3 = optimize("H3")

    candidates = {
        "H0": (chi0, 0, None, []),
        "H1": (
            chi1,
            1,
            None,
            [float(amp1)],
        ),
        "H2": (
            chi2,
            3,
            shift2,
            amps2,
        ),
        "H3": (
            chi3,
            4,
            shift3,
            amps3,
        ),
    }

    models = {}

    for hypothesis, (
        chi,
        parameters,
        shift,
        amplitudes,
    ) in candidates.items():

        bic = float(
            chi + parameters * np.log(n)
        )

        models[hypothesis] = {
            "bic": bic,
            "chi2": float(chi),
            "shift_dx_dy_px": shift,
            "amplitudes": amplitudes,
        }

    ranking = sorted(
        models,
        key=lambda h: models[h]["bic"],
    )

    best = ranking[0]
    second = ranking[1]

    return {
        "best_hypothesis": best,
        "classification": LABELS[best],
        "delta_bic_to_second": (
            models[second]["bic"]
            - models[best]["bic"]
        ),
        "models": models,
    }


# ==========================================================
# 7. PRUEBA COMPLETA DE MORLEY
# ==========================================================

def run_demo(
    outdir,
    seed=42,
    flux=260.0,
    noise_sigma=0.7,
):
    """
    Ejecuta:

    RA/Dec
       ↓
    Movimiento propio temporal
       ↓
    Conversión WCS a píxeles
       ↓
    Generación de dos imágenes sintéticas
       ↓
    ZOGY
       ↓
    MORLEY Model Comparator
    """

    size = 128

    mjd1 = BARNARD["reference_mjd"]
    mjd2 = mjd1 + 365.25

    # Posición época 1
    ra1, dec1 = propagate_pm(
        BARNARD["ra_deg"],
        BARNARD["dec_deg"],
        mjd1,
        mjd1,
        BARNARD["pm_ra_cosdec_masyr"],
        BARNARD["pm_dec_masyr"],
    )

    # Posición época 2
    ra2, dec2 = propagate_pm(
        BARNARD["ra_deg"],
        BARNARD["dec_deg"],
        mjd1,
        mjd2,
        BARNARD["pm_ra_cosdec_masyr"],
        BARNARD["pm_dec_masyr"],
    )

    # Proyección astrométrica
    wcs, wcs_mode = make_wcs(
        ra1,
        dec1,
        size,
        6.2,
    )

    x1, y1 = world_to_pixel(
        wcs,
        ra1,
        dec1,
    )

    x2, y2 = world_to_pixel(
        wcs,
        ra2,
        dec2,
    )

    # Desplazamiento esperado
    dx = x2 - x1
    dy = y2 - y1

    # PSF sintética
    psf = gaussian_psf()

    rng = np.random.default_rng(seed)

    # Estrellas de fondo estacionarias
    background = np.zeros(
        (size, size),
        float,
    )

    for bx, by, bf in [
        (28, 35, 120),
        (95, 86, 85),
        (37, 99, 130),
        (105, 27, 90),
    ]:

        background += stamp_source(
            (size, size),
            psf,
            bx,
            by,
            bf,
        )

    # Primera imagen
    reference = (
        background
        + stamp_source(
            (size, size),
            psf,
            x1,
            y1,
            flux,
        )
        + rng.normal(
            0,
            noise_sigma,
            (size, size),
        )
    )

    # Segunda imagen
    new = (
        background
        + stamp_source(
            (size, size),
            psf,
            x2,
            y2,
            flux,
        )
        + rng.normal(
            0,
            noise_sigma,
            (size, size),
        )
    )

    # Aplicar ZOGY
    z = zogy(
        reference,
        new,
        psf,
        psf,
        noise_sigma,
        noise_sigma,
    )

    # Comparar hipótesis
    comparison = compare_models(
        z.difference,
        z.psf_d,
        (y1, x1),
    )

    # Movimiento recuperado
    shift = comparison[
        "models"
    ]["H2"]["shift_dx_dy_px"]

    error = float(
        np.hypot(
            shift[0] - dx,
            shift[1] - dy,
        )
    )

    # Resultados
    result = {
        "mode": "SIMULACION_NO_SPHEREX",
        "wcs_implementation": wcs_mode,
        "position_epoch_1": {
            "mjd": mjd1,
            "ra_deg": ra1,
            "dec_deg": dec1,
            "pixel_x": x1,
            "pixel_y": y1,
        },
        "position_epoch_2": {
            "mjd": mjd2,
            "ra_deg": ra2,
            "dec_deg": dec2,
            "pixel_x": x2,
            "pixel_y": y2,
        },
        "expected_shift_dx_dy_px": [
            dx,
            dy,
        ],
        "expected_motion_arcsec": float(
            np.hypot(
                BARNARD["pm_ra_cosdec_masyr"],
                BARNARD["pm_dec_masyr"],
            ) / 1000
        ),
        "recovered_shift_dx_dy_px": shift,
        "recovered_shift_error_px": error,
        "peak_ideal_snr": float(
            np.max(
                np.abs(z.significance)
            )
        ),
        "morley": comparison,
        "limitations": [
            "Sin paralaje de SPHEREx",
            "PSF y ruido sintéticos",
            "Sin S_corr completo",
            "Sin validación en FITS reales",
        ],
    }

    # Guardar resultados locales
    outdir = Path(outdir)

    outdir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (outdir / "analysis.json").write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    np.savez_compressed(
        outdir / "products.npz",
        reference=reference,
        new=new,
        difference=z.difference,
        significance=z.significance,
        psf_d=z.psf_d,
    )

    # Visualización opcional
    try:
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(
            1,
            4,
            figsize=(13, 3.4),
        )

        images = [
            reference,
            new,
            z.difference,
            z.significance,
        ]

        titles = [
            "Época 1",
            "Época 2",
            "D (ZOGY)",
            "SNR ideal",
        ]

        for ax, arr, title in zip(
            axes,
            images,
            titles,
        ):

            ax.imshow(
                arr,
                origin="lower",
                cmap="gray",
            )

            ax.set_title(title)

            ax.set_xlim(
                x1 - 15,
                x1 + 15,
            )

            ax.set_ylim(
                y1 - 15,
                y1 + 15,
            )

        fig.tight_layout()

        fig.savefig(
            outdir / "comparison.png",
            dpi=140,
        )

        plt.close(fig)

    except ImportError:
        pass

    # Resultados en consola
    print("\n" + "=" * 55)
    print("MORLEY FRONTIER — SCIENTIFIC RESULTS")
    print("=" * 55)

    print("\nWCS:", wcs_mode)

    print("\nRA/Dec inicial:")
    print(ra1, dec1)

    print("\nRA/Dec final:")
    print(ra2, dec2)

    print("\nDesplazamiento esperado (dx,dy):")
    print(np.round([dx, dy], 4))

    print("\nDesplazamiento recuperado H2:")
    print(np.round(shift, 4))

    print("\nError en píxeles:")
    print(round(error, 4))

    print("\nMejor hipótesis:")
    print(
        comparison["best_hypothesis"],
        comparison["classification"],
    )

    print("\nDelta BIC:")
    print(
        round(
            comparison["delta_bic_to_second"],
            3,
        )
    )

    print("\nPeak |SNR| ideal:")
    print(
        round(
            result["peak_ideal_snr"],
            3,
        )
    )

    print("\nResultados:")
    print(outdir.resolve())

    return result


# ==========================================================
# 8. EJECUCIÓN
# ==========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "MORLEY: RA/Dec -> WCS -> "
            "ZOGY -> Comparator"
        )
    )

    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecutar prueba sintética unificada",
    )

    parser.add_argument(
        "--out",
        default="morley_resultados",
        help="Carpeta para resultados",
    )

    args = parser.parse_args()

    if not args.demo:
        parser.error(
            "Esta versión utiliza --demo. "
            "Los FITS reales requieren "
            "calibración y registro previo."
        )

    run_demo(args.out)
