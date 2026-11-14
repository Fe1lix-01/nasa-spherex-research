
"""
MORLEY Frontier
Astrometría exploratoria con ajuste gaussiano ponderado.

Este script:
1. Lee la mejor pareja SPHEREx del CSV.
2. Ajusta una gaussiana circular a las fuentes A y B.
3. Pondera cada píxel mediante VARIANCE.
4. Calcula chi-cuadrada y chi-cuadrada reducida.
5. Estima la covarianza formal de cada centroide.
6. Propaga incertidumbres a coordenadas celestes.
7. Compara desplazamientos entre ambas épocas.

IMPORTANTE:
Las incertidumbres son formales. No incluyen errores
sistemáticos del WCS, paralaje, ePSF instrumental,
mezclas de fuentes o correlación espacial del ruido.

NO constituye una detección validada de movimiento.
"""

import csv
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.optimize import least_squares


# =====================================================
# CONFIGURACIÓN
# =====================================================

FUENTES = {
    "A": (22.0, 6.0),
    "B": (15.0, 4.0),
}

RADIO = 3

# Bits instrumentales que rechazamos inicialmente.
# SOURCE (bit 21) se conserva.
BITS_MALOS = [
    0, 1, 2, 6, 7, 9, 10, 11,
    14, 15, 17, 19, 20, 22,
]

MASCARA_MALA = sum(1 << bit for bit in BITS_MALOS)


# =====================================================
# 1. LECTURA DE FITS
# =====================================================

def cargar_fits(ruta):

    ruta = Path(ruta)

    if not ruta.is_file():
        raise FileNotFoundError(
            f"FITS no encontrado: {ruta}"
        )

    with fits.open(ruta, memmap=False) as hdul:

        hdu = hdul["IMAGE"]

        return {
            "image": np.array(
                hdu.data,
                dtype=float,
                copy=True
            ),

            "variance": np.array(
                hdul["VARIANCE"].data,
                dtype=float,
                copy=True
            ),

            "flags": np.array(
                hdul["FLAGS"].data,
                dtype=np.int64,
                copy=True
            ),

            "wcs": WCS(
                hdu.header,
                fobj=hdul
            ).celestial,

            "date": hdu.header.get(
                "DATE-OBS",
                "DESCONOCIDA"
            ),

            "obsid": hdu.header.get(
                "OBSID",
                "DESCONOCIDO"
            ),
        }


def numero_unico(valor):
    return float(np.asarray(valor).item())


# =====================================================
# 2. AJUSTE GAUSSIANO PONDERADO
# =====================================================

def medir_centro(datos, x0, y0, radio=RADIO):

    imagen = datos["image"]
    varianza = datos["variance"]
    flags = datos["flags"]

    alto, ancho = imagen.shape

    x0 = float(x0)
    y0 = float(y0)

    ix = int(round(x0))
    iy = int(round(y0))

    xa = max(0, ix - radio)
    xb = min(ancho, ix + radio + 1)

    ya = max(0, iy - radio)
    yb = min(alto, iy + radio + 1)

    yy, xx = np.mgrid[ya:yb, xa:xb]

    subimagen = imagen[ya:yb, xa:xb]
    subvar = varianza[ya:yb, xa:xb]
    subflags = flags[ya:yb, xa:xb]

    # Filtrado de píxeles
    validos = (
        np.isfinite(subimagen)
        & np.isfinite(subvar)
        & (subvar > 0)
        & ((subflags & MASCARA_MALA) == 0)
    )

    n = int(validos.sum())

    if n < 15:
        raise ValueError(
            f"Solo {n} píxeles utilizables"
        )

    x = xx[validos].astype(float)
    y = yy[validos].astype(float)

    z = subimagen[validos]

    # Error individual de cada píxel
    sigma_p = np.sqrt(subvar[validos])

    fondo0 = float(np.median(z))

    amplitud0 = max(
        float(np.max(z) - fondo0),
        1e-6
    )

    # -------------------------------------------------
    # Modelo gaussiano circular 2D
    # -------------------------------------------------

    def residuales(p):

        amp, cx, cy, sigma, fondo = p

        modelo = fondo + amp * np.exp(
            -(
                (x - cx)**2
                + (y - cy)**2
            ) / (2 * sigma**2)
        )

        # Residuales normalizados por incertidumbre
        return (z - modelo) / sigma_p

    # -------------------------------------------------
    # Optimización
    # -------------------------------------------------

    limites_inferiores = [
        0,
        x0 - 1.5,
        y0 - 1.5,
        0.55,
        -np.inf,
    ]

    limites_superiores = [
        np.inf,
        x0 + 1.5,
        y0 + 1.5,
        3.0,
        np.inf,
    ]

    ajuste = least_squares(
        residuales,

        x0=[
            amplitud0,
            x0,
            y0,
            1.2,
            fondo0,
        ],

        bounds=(
            limites_inferiores,
            limites_superiores
        ),

        method="trf",
        max_nfev=1000,
    )

    if not ajuste.success:
        raise ValueError(
            f"El ajuste no convergió: {ajuste.message}"
        )

    amp, cx, cy, sigma, fondo = [
        float(v) for v in ajuste.x
    ]

    if (
        abs(cx - x0) > 1.48
        or abs(cy - y0) > 1.48
    ):
        raise ValueError(
            "Centroide en el límite permitido"
        )

    if sigma < 0.56 or sigma > 2.99:
        raise ValueError(
            "Anchura gaussiana en el límite"
        )

    # =================================================
    # 3. CHI CUADRADA
    # =================================================

    numero_parametros = len(ajuste.x)

    grados_libertad = n - numero_parametros

    if grados_libertad <= 0:
        raise ValueError(
            "Grados de libertad insuficientes"
        )

    chi2 = float(
        np.sum(ajuste.fun**2)
    )

    chi2_reducido = (
        chi2 / grados_libertad
    )

    # =================================================
    # 4. MATRIZ DE COVARIANZA
    # =================================================

    J = ajuste.jac

    if np.linalg.matrix_rank(J) < numero_parametros:
        raise ValueError(
            "Jacobiano degenerado"
        )

    informacion = J.T @ J

    covarianza = np.linalg.inv(informacion)

    # Inflar errores si la dispersión excede
    # la esperada por el modelo de varianza.
    factor = max(1.0, chi2_reducido)

    covarianza *= factor

    # Parámetros 1 y 2: centro X, centro Y
    cov_xy = covarianza[
        np.ix_([1, 2], [1, 2])
    ]

    errores = np.sqrt(
        np.diag(cov_xy)
    )

    return {
        "x": cx,
        "y": cy,

        "sigma_x": float(errores[0]),
        "sigma_y": float(errores[1]),

        "cov_xy": cov_xy,

        "chi2": chi2,
        "chi2_reducido": chi2_reducido,

        "dof": grados_libertad,
        "n_pix": n,

        "amplitud": amp,
        "ancho_sigma_px": sigma,
        "fondo": fondo,

        "ventana_recortada": (
            xa == 0
            or ya == 0
            or xb == ancho
            or yb == alto
        ),
    }


# =====================================================
# 5. PROPAGACIÓN DE ERRORES AL WCS
# =====================================================

def error_celeste(datos, medida):

    wcs = datos["wcs"]

    x = medida["x"]
    y = medida["y"]

    punto = wcs.pixel_to_world(x, y)

    # Diferencias finitas para el Jacobiano local
    h = 0.01

    dx = wcs.pixel_to_world(x + h, y)
    dy = wcs.pixel_to_world(x, y + h)

    ex, nx = punto.spherical_offsets_to(dx)
    ey, ny = punto.spherical_offsets_to(dy)

    jac = np.array([
        [
            ex.arcsec / h,
            ey.arcsec / h,
        ],

        [
            nx.arcsec / h,
            ny.arcsec / h,
        ],
    ])

    cov_en = (
        jac
        @ medida["cov_xy"]
        @ jac.T
    )

    return punto, cov_en


# =====================================================
# 6. PROGRAMA PRINCIPAL
# =====================================================

def main():

    ruta_csv = Path(
        "parejas_ordenadas.csv"
    )

    if not ruta_csv.is_file():
        raise SystemExit(
            "No encuentro parejas_ordenadas.csv"
        )

    with ruta_csv.open(
        encoding="utf-8-sig",
        newline=""
    ) as f:

        filas = list(
            csv.DictReader(f)
        )

    if not filas:
        raise SystemExit(
            "El CSV no contiene parejas"
        )

    mejor = min(
        filas,
        key=lambda fila: float(
            fila["desajuste"]
        )
    )

    a = cargar_fits(
        mejor["archivo_2025"]
    )

    b = cargar_fits(
        mejor["archivo_2026"]
    )

    print("\n" + "=" * 60)
    print("MORLEY — ASTROMETRÍA GAUSSIANA AJUSTADA")
    print("=" * 60)

    print(
        f"2025: {a['date']} | {a['obsid']}"
    )

    print(
        f"2026: {b['date']} | {b['obsid']}"
    )

    print(
        "Desajuste espectral:",
        mejor["desajuste"]
    )

    resultados = {}

    # =================================================
    # 7. MEDICIÓN POR FUENTE
    # =================================================

    for nombre, (x0, y0) in FUENTES.items():

        print("\n" + "-" * 55)
        print("FUENTE:", nombre)

        try:

            # Medición directa en 2025
            m1 = medir_centro(
                a,
                x0,
                y0
            )

            # Posición celeste de la semilla visual
            ra0, dec0 = (
                a["wcs"].pixel_to_world_values(
                    x0,
                    y0
                )
            )

            # Proyección de la semilla hacia 2026
            xp, yp = (
                b["wcs"].world_to_pixel_values(
                    ra0,
                    dec0
                )
            )

            xp = numero_unico(xp)
            yp = numero_unico(yp)

            # Medición independiente en 2026
            m2 = medir_centro(
                b,
                xp,
                yp
            )

            # Conversión de los centroides a cielo
            s1, c1 = error_celeste(a, m1)
            s2, c2 = error_celeste(b, m2)

            este, norte = (
                s1.spherical_offsets_to(s2)
            )

            de = float(este.arcsec)
            dn = float(norte.arcsec)

            # Incertidumbre estadística formal
            cov_delta = c1 + c2

            sigma_este, sigma_norte = (
                np.sqrt(np.diag(cov_delta))
            )

            # -----------------------------------------
            # Resultados de centroides
            # -----------------------------------------

            print(
                f"\n2025 centro: "
                f"({m1['x']:.4f}, {m1['y']:.4f}) px"
            )

            print(
                f"2026 centro: "
                f"({m2['x']:.4f}, {m2['y']:.4f}) px"
            )

            # -----------------------------------------
            # Calidad de cada ajuste
            # -----------------------------------------

            for anio, med in [
                (2025, m1),
                (2026, m2)
            ]:

                print(f"\nAJUSTE {anio}")

                print(
                    f"Sigma X: "
                    f"{med['sigma_x']:.5f} px"
                )

                print(
                    f"Sigma Y: "
                    f"{med['sigma_y']:.5f} px"
                )

                print(
                    f"Chi2: {med['chi2']:.4f}"
                )

                print(
                    f"Chi2 reducido: "
                    f"{med['chi2_reducido']:.4f}"
                )

                print(
                    f"Grados de libertad: "
                    f"{med['dof']}"
                )

                print(
                    f"Pixeles utilizados: "
                    f"{med['n_pix']}"
                )

                print(
                    f"Anchura gaussiana: "
                    f"{med['ancho_sigma_px']:.4f} px"
                )

                if med["ventana_recortada"]:
                    print(
                        "ADVERTENCIA: ventana "
                        "recortada por el borde"
                    )

            # -----------------------------------------
            # Resultados astrométricos
            # -----------------------------------------

            print("\nPOSICIONES CELESTES")

            print(
                f"2025 RA: {s1.ra.deg:.8f}"
                f" | Dec: {s1.dec.deg:.8f}"
            )

            print(
                f"2026 RA: {s2.ra.deg:.8f}"
                f" | Dec: {s2.dec.deg:.8f}"
            )

            print("\nDESPLAZAMIENTO APARENTE")

            print(
                f"Este: {de:+.4f} "
                f"± {sigma_este:.4f} arcsec"
            )

            print(
                f"Norte: {dn:+.4f} "
                f"± {sigma_norte:.4f} arcsec"
            )

            magnitud = np.hypot(
                de,
                dn
            )

            print(
                f"Magnitud aparente: "
                f"{magnitud:.4f} arcsec"
            )

            resultados[nombre] = (
                np.array([de, dn]),
                cov_delta
            )

        except Exception as error:
            print(
                f"No se pudo evaluar "
                f"{nombre}: {error}"
            )

    # =================================================
    # 8. COMPARACIÓN DIFERENCIAL
    # =================================================

    if (
        "A" in resultados
        and "B" in resultados
    ):

        delta_a, cov_a = resultados["A"]
        delta_b, cov_b = resultados["B"]

        diferencia = (
            delta_a - delta_b
        )

        # Aproximación: no incluye correlaciones
        # sistemáticas compartidas por ambas fuentes.
        cov_diferencial = (
            cov_a + cov_b
        )

        sigma = np.sqrt(
            np.diag(cov_diferencial)
        )

        print("\n" + "=" * 60)
        print("COMPARACIÓN DIFERENCIAL A - B")
        print("=" * 60)

        print(
            f"Este: {diferencia[0]:+.4f} "
            f"± {sigma[0]:.4f} arcsec"
        )

        print(
            f"Norte: {diferencia[1]:+.4f} "
            f"± {sigma[1]:.4f} arcsec"
        )

    print("\n" + "=" * 60)
    print("INTERPRETACIÓN CIENTÍFICA")
    print("=" * 60)

    print(
        "Las incertidumbres reportadas son "
        "errores estadísticos formales."
    )

    print(
        "No incluyen sistemáticos del WCS, "
        "paralaje ni sesgos de PSF."
    )

    print(
        "Un chi2 reducido elevado puede indicar "
        "un modelo gaussiano inadecuado, "
        "fuentes mezcladas o ruido mal modelado."
    )

    print(
        "No interpretar estos valores "
        "como detección física de movimiento."
    )


if __name__ == "__main__":
    main()
