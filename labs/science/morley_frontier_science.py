
import argparse
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint

import numpy as np
from scipy.ndimage import shift as shift_image
from scipy.optimize import minimize, nnls


# ==========================================================
# PARTE 1: RA / DEC + TEMPORALIDAD
# ==========================================================

def predict_position(
    ra_deg,
    dec_deg,
    reference_mjd,
    epoch_mjd,
    pm_ra_cosdec_masyr,
    pm_dec_masyr,
):
    """
    Propaga la posición celeste mediante movimiento propio.

    RA, Dec: grados
    MJD: fecha juliana modificada
    pm_ra_cosdec_masyr: movimiento RA*cos(Dec) en mas/año
    pm_dec_masyr: movimiento Dec en mas/año

    Aproximación local para desplazamientos pequeños.
    No incluye paralaje ni efectos de perspectiva.
    """

    dt_yr = (
        float(epoch_mjd) - float(reference_mjd)
    ) / 365.25

    cosdec = np.cos(np.deg2rad(dec_deg))

    if abs(cosdec) < 1e-8:
        raise ValueError(
            "Demasiado cerca de los polos celestes"
        )

    delta_ra = (
        pm_ra_cosdec_masyr
        / 3.6e6
        / cosdec
    ) * dt_yr

    delta_dec = (
        pm_dec_masyr / 3.6e6
    ) * dt_yr

    ra_new = (ra_deg + delta_ra) % 360.0
    dec_new = dec_deg + delta_dec

    motion_arcsec = (
        np.hypot(
            pm_ra_cosdec_masyr,
            pm_dec_masyr,
        )
        * abs(dt_yr)
        / 1000.0
    )

    return {
        "mjd": float(epoch_mjd),
        "ra_deg": float(ra_new),
        "dec_deg": float(dec_new),
        "elapsed_years": float(dt_yr),
        "predicted_proper_motion_arcsec": float(
            motion_arcsec
        ),
        "model": "small_angle_proper_motion_only",
    }


def compare_epochs(
    ra_deg,
    dec_deg,
    reference_mjd,
    new_mjd,
    pm_ra_cosdec_masyr,
    pm_dec_masyr,
):
    reference = predict_position(
        ra_deg,
        dec_deg,
        reference_mjd,
        reference_mjd,
        pm_ra_cosdec_masyr,
        pm_dec_masyr,
    )

    new = predict_position(
        ra_deg,
        dec_deg,
        reference_mjd,
        new_mjd,
        pm_ra_cosdec_masyr,
        pm_dec_masyr,
    )

    return {
        "reference": reference,
        "new": new,
    }


# ==========================================================
# PARTE 2: ZOGY — PROPER IMAGE SUBTRACTION
# ==========================================================

@dataclass
class ZogyResult:
    difference: np.ndarray
    significance: np.ndarray
    psf_difference: np.ndarray
    difference_flux_scale: float
    noise_std_difference: float


def _psf_fft(psf, shape):
    """
    Normaliza la PSF, la coloca en el centro
    de la imagen y calcula su transformada FFT.
    """

    p = np.asarray(psf, dtype=float)

    if p.ndim != 2:
        raise ValueError("La PSF debe ser 2D")

    if any(s > n for s, n in zip(p.shape, shape)):
        raise ValueError(
            "La PSF no puede ser mayor que la imagen"
        )

    if not np.isfinite(p).all() or p.sum() <= 0:
        raise ValueError("PSF inválida")

    p = p / p.sum()

    canvas = np.zeros(shape, dtype=float)

    cy = shape[0] // 2 - p.shape[0] // 2
    cx = shape[1] // 2 - p.shape[1] // 2

    canvas[
        cy:cy + p.shape[0],
        cx:cx + p.shape[1],
    ] = p

    return np.fft.fft2(
        np.fft.ifftshift(canvas)
    )


def zogy_difference(
    reference,
    new,
    psf_ref,
    psf_new,
    sigma_ref,
    sigma_new,
    flux_ref=1.0,
    flux_new=1.0,
):
    """
    ZOGY idealizado: ecuaciones 13–16.

    Entradas:
        reference: imagen época 1
        new: imagen época 2
        psf_ref: PSF referencia
        psf_new: PSF nueva
        sigma_ref: ruido de fondo referencia
        sigma_new: ruido de fondo nueva

    Devuelve:
        D: diferencia propia
        SNR: mapa de significancia ideal
        P_D: PSF efectiva

    Ambas imágenes deben tener:
        - Mismo sistema WCS
        - Misma escala
        - Respuesta espectral compatible
        - Calibración fotométrica consistente
        - Ruido aproximadamente gaussiano blanco
    """

    r = np.asarray(reference, dtype=float)
    n = np.asarray(new, dtype=float)

    if r.ndim != 2 or r.shape != n.shape:
        raise ValueError(
            "Las imágenes deben ser 2D y de igual tamaño"
        )

    if min(r.shape) < 10:
        raise ValueError("Imágenes demasiado pequeñas")

    if not np.isfinite(r).all():
        raise ValueError("Referencia contiene NaN/Inf")

    if not np.isfinite(n).all():
        raise ValueError("Nueva imagen contiene NaN/Inf")

    if min(
        sigma_ref,
        sigma_new,
        flux_ref,
        flux_new,
    ) <= 0:
        raise ValueError(
            "Ruido y factores de flujo deben ser positivos"
        )

    # PSF en Fourier
    pr = _psf_fft(psf_ref, r.shape)
    pn = _psf_fft(psf_new, r.shape)

    # Imágenes en Fourier
    rh = np.fft.fft2(r)
    nh = np.fft.fft2(n)

    # Denominador ZOGY
    power = (
        sigma_new**2
        * flux_ref**2
        * np.abs(pr)**2
        +
        sigma_ref**2
        * flux_new**2
        * np.abs(pn)**2
    )

    denominator = np.sqrt(power)

    good = denominator > (
        1e-12 * np.max(denominator)
    )

    # Imagen de diferencia propia
    dh = np.zeros_like(nh, dtype=complex)

    numerator = (
        flux_ref * pr * nh
        -
        flux_new * pn * rh
    )

    dh[good] = (
        numerator[good] / denominator[good]
    )

    # Factor de flujo de diferencia
    fd = (
        flux_ref * flux_new
        /
        np.hypot(
            sigma_new * flux_ref,
            sigma_ref * flux_new,
        )
    )

    # PSF efectiva
    pdh = np.zeros_like(nh, dtype=complex)

    pdh[good] = (
        flux_ref
        * flux_new
        * pr[good]
        * pn[good]
        /
        (fd * denominator[good])
    )

    # Regreso al espacio de píxeles
    d = np.fft.ifft2(dh).real

    pd = np.fft.fftshift(
        np.fft.ifft2(pdh).real
    )

    norm = float(np.linalg.norm(pd))

    if norm < 1e-12:
        raise ValueError("PSF efectiva degenerada")

    # Filtro adaptado normalizado
    significance = (
        np.fft.ifft2(
            dh * np.conj(pdh)
        ).real
        / norm
    )

    return ZogyResult(
        difference=d,
        significance=significance,
        psf_difference=pd,
        difference_flux_scale=float(fd),
        noise_std_difference=1.0,
    )


# ==========================================================
# PARTE 3: MORLEY MODEL COMPARATOR
# ==========================================================

LABELS = {
    "H0": "sin_cambio",
    "H1": "variabilidad",
    "H2": "movimiento",
    "H3": "movimiento_y_variabilidad",
}


def _fit_amplitudes(y, columns):
    """
    Ajuste por mínimos cuadrados con amplitudes
    no negativas.
    """

    matrix = np.column_stack(columns)

    coefficients, _ = nnls(matrix, y)

    residual = y - matrix @ coefficients

    return (
        float(residual @ residual),
        coefficients,
    )


def compare_models(
    difference,
    psf_difference,
    center_yx,
    max_shift_px=3.5,
    roi_radius_px=11,
):
    """
    Compara cuatro hipótesis:

    H0 = sin cambio
    H1 = cambio de brillo
    H2 = movimiento
    H3 = movimiento + variabilidad

    Utiliza ajuste de PSF y criterio BIC.
    """

    d = np.asarray(difference, dtype=float)
    p = np.asarray(psf_difference, dtype=float)

    if d.shape != p.shape or d.ndim != 2:
        raise ValueError(
            "D y P_D deben tener el mismo tamaño 2D"
        )

    if not np.isfinite(d).all():
        raise ValueError("D contiene valores inválidos")

    if not np.isfinite(p).all():
        raise ValueError("P_D contiene valores inválidos")

    if max_shift_px <= 0:
        raise ValueError("max_shift_px debe ser positivo")

    cy, cx = map(float, center_yx)

    radius = int(roi_radius_px)

    iy = int(round(cy))
    ix = int(round(cx))

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
            "La fuente está demasiado cerca del borde"
        )

    data = d[y0:y1, x0:x1].ravel()

    n_pixels = data.size

    def template(dx, dy):
        shifted = shift_image(
            p,
            shift=(
                cy - p.shape[0] // 2 + dy,
                cx - p.shape[1] // 2 + dx,
            ),
            order=3,
            mode="constant",
            cval=0.0,
            prefilter=True,
        )

        return shifted[
            y0:y1,
            x0:x1,
        ].ravel()

    # Plantilla original
    p0 = template(0.0, 0.0)

    # H0: sin cambio
    chi0 = float(data @ data)

    # H1: variabilidad
    denominator = float(p0 @ p0)

    amplitude = (
        float(data @ p0) / denominator
        if denominator > 0
        else 0.0
    )

    chi1 = float(
        np.sum((data - amplitude * p0)**2)
    )

    # H2: movimiento con flujo constante
    # H3: movimiento y cambio de flujo
    def objective(offset, model):
        dx, dy = offset

        shifted = template(dx, dy)

        if model == "H2":
            basis = shifted - p0

            amp = max(
                0.0,
                float(data @ basis)
                /
                max(1e-15, float(basis @ basis)),
            )

            residual = data - amp * basis

            return float(
                np.sum(residual**2)
            ), [amp]

        # H3
        return _fit_amplitudes(
            data,
            [shifted, -p0],
        )

    def optimize(model):
        limit = float(max_shift_px)

        seeds = [
            (float(dx), float(dy))
            for dx in np.linspace(-limit, limit, 5)
            for dy in np.linspace(-limit, limit, 5)
        ]

        best = (
            np.inf,
            None,
            None,
        )

        for seed in seeds:
            result = minimize(
                lambda z: objective(z, model)[0],
                x0=seed,
                bounds=[
                    (-limit, limit),
                    (-limit, limit),
                ],
                method="L-BFGS-B",
                options={"maxiter": 50},
            )

            chi, amplitudes = objective(
                result.x,
                model,
            )

            if chi < best[0]:
                best = (
                    chi,
                    result.x,
                    amplitudes,
                )

        return best

    chi2, shift2, amps2 = optimize("H2")
    chi3, shift3, amps3 = optimize("H3")

    raw = {
        "H0": (chi0, 0, None, []),
        "H1": (chi1, 1, None, [amplitude]),
        "H2": (chi2, 3, shift2, amps2),
        "H3": (chi3, 4, shift3, amps3),
    }

    models = {}

    for hypothesis, (
        chi,
        n_parameters,
        shift_xy,
        amplitudes,
    ) in raw.items():

        bic = (
            float(chi)
            +
            n_parameters * np.log(n_pixels)
        )

        models[hypothesis] = {
            "label": LABELS[hypothesis],
            "chi2": float(chi),
            "bic": float(bic),
            "n_parameters": n_parameters,
            "shift_dx_dy_pixels": (
                None
                if shift_xy is None
                else [
                    float(v) for v in shift_xy
                ]
            ),
            "amplitudes": [
                float(a) for a in amplitudes
            ],
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
        "delta_bic_to_second": float(
            models[second]["bic"]
            - models[best]["bic"]
        ),
        "models": models,
    }


# ==========================================================
# PARTE 4: PIPELINE CIENTÍFICO
# ==========================================================

def analyze(
    reference,
    new,
    psf_ref,
    psf_new,
    sigma_ref,
    sigma_new,
    center_yx,
    ra_deg,
    dec_deg,
    reference_mjd,
    new_mjd,
    pm_ra_cosdec_masyr=-802.803,
    pm_dec_masyr=10362.5,
):
    """
    Ejecuta las tres piezas principales.

    Las imágenes deben corresponder a exposiciones
    independientes y previamente preparadas.
    """

    if new_mjd <= reference_mjd:
        raise ValueError(
            "La nueva época debe ser posterior"
        )

    # 1. Astrometría
    astrometry = compare_epochs(
        ra_deg,
        dec_deg,
        reference_mjd,
        new_mjd,
        pm_ra_cosdec_masyr,
        pm_dec_masyr,
    )

    # 2. ZOGY
    zogy = zogy_difference(
        reference,
        new,
        psf_ref,
        psf_new,
        sigma_ref,
        sigma_new,
    )

    # 3. MORLEY
    comparison = compare_models(
        zogy.difference,
        zogy.psf_difference,
        center_yx,
    )

    return {
        "astrometry": astrometry,
        "zogy": zogy,
        "comparison": comparison,
    }


# ==========================================================
# PARTE 5: SIMULACIÓN DE PRUEBA
# ==========================================================

def generate_demo():
    """
    Genera dos imágenes sintéticas con una estrella
    que se mueve entre épocas.
    """

    rng = np.random.default_rng(42)

    size = 80

    grid_y, grid_x = np.mgrid[
        -10:11,
        -10:11,
    ]

    # PSF gaussiana sintética
    psf = np.exp(
        -(grid_x**2 + grid_y**2)
        / (2 * 1.6**2)
    )

    psf /= psf.sum()

    canvas = np.zeros((size, size))

    canvas[30:51, 30:51] = psf

    # Época 1
    reference = (
        200 * canvas
        +
        rng.normal(
            0, 0.7, canvas.shape
        )
    )

    # Época 2: fuente desplazada
    new = (
        200 * shift_image(
            canvas,
            shift=(-0.65, 1.65),
            order=3,
            mode="constant",
        )
        +
        rng.normal(
            0, 0.7, canvas.shape
        )
    )

    return reference, new, psf


# ==========================================================
# PARTE 6: EJECUCIÓN
# ==========================================================

def main():
    parser = argparse.ArgumentParser(
        description="MORLEY Frontier Scientific Engine"
    )

    source = parser.add_mutually_exclusive_group(
        required=True
    )

    source.add_argument(
        "--demo",
        action="store_true",
    )

    source.add_argument(
        "--npz",
        type=Path,
    )

    parser.add_argument("--cy", type=float, default=40)
    parser.add_argument("--cx", type=float, default=40)

    parser.add_argument(
        "--ra",
        type=float,
        default=269.4463,
    )

    parser.add_argument(
        "--dec",
        type=float,
        default=4.7682,
    )

    parser.add_argument(
        "--mjd-ref",
        type=float,
        default=60970.0,
    )

    parser.add_argument(
        "--mjd-new",
        type=float,
        default=61335.25,
    )

    args = parser.parse_args()

    if args.demo:
        reference, new, psf = generate_demo()

        psf_ref = psf
        psf_new = psf

        sigma_ref = 0.7
        sigma_new = 0.7

    else:
        with np.load(
            args.npz,
            allow_pickle=False,
        ) as data:

            required = {
                "reference",
                "new",
                "psf_ref",
                "psf_new",
                "sigma_ref",
                "sigma_new",
            }

            missing = required - set(data.files)

            if missing:
                raise ValueError(
                    f"Faltan datos: {sorted(missing)}"
                )

            if (
                "sha256_ref" in data.files
                and "sha256_new" in data.files
                and
                data["sha256_ref"].item()
                == data["sha256_new"].item()
            ):
                raise ValueError(
                    "Los FITS de ambas épocas son idénticos"
                )

            reference = data["reference"].copy()
            new = data["new"].copy()

            psf_ref = data["psf_ref"].copy()
            psf_new = data["psf_new"].copy()

            sigma_ref = float(data["sigma_ref"])
            sigma_new = float(data["sigma_new"])

    result = analyze(
        reference=reference,
        new=new,
        psf_ref=psf_ref,
        psf_new=psf_new,
        sigma_ref=sigma_ref,
        sigma_new=sigma_new,
        center_yx=(args.cy, args.cx),
        ra_deg=args.ra,
        dec_deg=args.dec,
        reference_mjd=args.mjd_ref,
        new_mjd=args.mjd_new,
    )

    print("\n" + "=" * 50)
    print("MORLEY FRONTIER — SCIENTIFIC RESULTS")
    print("=" * 50)

    print("\nASTROMETRÍA RA/DEC:")
    pprint(result["astrometry"])

    print("\nMORLEY MODEL COMPARATOR:")
    pprint(result["comparison"])

    zogy = result["zogy"]

    print("\nZOGY:")
    print("D shape:", zogy.difference.shape)
    print(
        "Peak |SNR|:",
        float(np.max(np.abs(zogy.significance)))
    )

    print(
        "\nADVERTENCIA: significancia ZOGY idealizada, "
        "sin corrección S_corr de la ecuación 25."
    )


if __name__ == "__main__":
    main()
