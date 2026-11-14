
"""
MORLEY Frontier
Ajuste instrumental ePSF vs gaussiana en SPHEREx.

Requiere:
    numpy, scipy, astropy, photutils, matplotlib

Colocar dentro de labs/science,
junto a parejas_ordenadas.csv.

No descarga observaciones.
No ejecuta ZOGY.
No confirma movimiento físico.
"""

import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from astropy.io import fits
from astropy.wcs import WCS
from scipy.optimize import least_squares

try:
    from photutils.psf import ImagePSF
except ImportError as exc:
    raise SystemExit(
        "Instala Photutils: "
        "python -m pip install photutils"
    ) from exc


# =====================================================
# 1. CONFIGURACIÓN
# =====================================================

CSV_PAREJAS = Path("parejas_ordenadas.csv")

SALIDA = Path("resultados_epsf_morley")

FUENTES = {
    "A": (22.0, 6.0),
    "B": (15.0, 4.0),
}

RADIO = 3

# Banderas instrumentales a rechazar.
# El bit 21 (SOURCE) permanece permitido.
BITS_MALOS = [
    0, 1, 2, 6, 7, 9, 10, 11,
    14, 15, 17, 19, 20, 22
]

BAD_MASK = sum(
    1 << bit for bit in BITS_MALOS
)


def escalar(valor):
    return float(np.asarray(valor).item())


# =====================================================
# 2. LECTURA DE DATOS FITS
# =====================================================

def leer_datos(archivo):

    archivo = Path(archivo)

    if not archivo.is_file():
        raise FileNotFoundError(
            f"FITS inexistente: {archivo}"
        )

    with fits.open(archivo, memmap=False) as h:

        head = h["IMAGE"].header

        if "EPSF" not in h:
            raise ValueError(
                f"No existe extensión EPSF: {archivo.name}"
            )

        if (
            "CRPIX1A" not in head
            or "CRPIX2A" not in head
        ):
            raise ValueError(
                "No hay CRPIX1A/CRPIX2A. "
                "No podemos ubicar la ePSF "
                "en el detector original."
            )

        tabla = h["EPSF"].data
        header_psf = h["EPSF"].header

        columnas = set(tabla.names)

        requeridas = [
            "EPSF",
            "XCENTER",
            "YCENTER",
            "BINX",
            "BINY",
        ]

        for nombre in requeridas:
            if nombre not in columnas:
                raise ValueError(
                    f"Falta columna EPSF/{nombre}"
                )

        datos = {

            "archivo": str(archivo),

            "image": np.array(
                h["IMAGE"].data,
                dtype=float,
                copy=True
            ),

            "variance": np.array(
                h["VARIANCE"].data,
                dtype=float,
                copy=True
            ),

            "flags": np.array(
                h["FLAGS"].data,
                dtype=np.int64,
                copy=True
            ),

            "wcs": WCS(
                head,
                fobj=h
            ).celestial,

            "fecha": head.get(
                "DATE-OBS",
                "desconocida"
            ),

            "obsid": head.get(
                "OBSID",
                "desconocido"
            ),

            "crpix1a": float(head["CRPIX1A"]),
            "crpix2a": float(head["CRPIX2A"]),

            "xcenters": np.array(
                tabla["XCENTER"],
                dtype=float,
                copy=True
            ),

            "ycenters": np.array(
                tabla["YCENTER"],
                dtype=float,
                copy=True
            ),

            "binx": np.array(
                tabla["BINX"],
                dtype=int,
                copy=True
            ),

            "biny": np.array(
                tabla["BINY"],
                dtype=int,
                copy=True
            ),

            "epsfs": np.array(
                tabla["EPSF"],
                dtype=float,
                copy=True
            ),

            "oversampling": (
                int(header_psf["OVSMPY"]),
                int(header_psf["OVSMPX"])
            ),
        }

    if not (
        datos["image"].shape
        == datos["variance"].shape
        == datos["flags"].shape
    ):
        raise ValueError(
            "IMAGE, VARIANCE y FLAGS "
            "tienen dimensiones incompatibles"
        )

    return datos


# =====================================================
# 3. SELECCIÓN DE LA ePSF INSTRUMENTAL
# =====================================================

def seleccionar_epsf(datos, x, y):

    # Transformación desde coordenadas del recorte
    # a coordenadas del detector original.
    xdet = (
        1 + float(x) - datos["crpix1a"]
    )

    ydet = (
        1 + float(y) - datos["crpix2a"]
    )

    distancias2 = (
        (datos["xcenters"] - xdet) ** 2
        + (datos["ycenters"] - ydet) ** 2
    )

    if not np.isfinite(distancias2).any():
        raise ValueError(
            "Centros de zonas ePSF no válidos"
        )

    zona = int(np.nanargmin(distancias2))

    imagen_psf = datos["epsfs"][zona]

    # La extensión EPSF puede almacenar
    # cada matriz como vector de 1089 elementos.
    if (
        imagen_psf.ndim == 1
        and imagen_psf.size == 1089
    ):
        imagen_psf = imagen_psf.reshape(33, 33)

    if (
        imagen_psf.ndim != 2
        or not np.all(np.isfinite(imagen_psf))
    ):
        raise ValueError(
            "La ePSF seleccionada no es válida"
        )

    if (
        not np.isfinite(imagen_psf.sum())
        or imagen_psf.sum() <= 0
    ):
        raise ValueError(
            "La ePSF no puede normalizarse"
        )

    # Modelo instrumental sobremuestreado,
    # evaluable en posiciones subpíxel.
    psf = ImagePSF(
        data=imagen_psf,
        oversampling=datos["oversampling"]
    )

    return psf, zona, xdet, ydet


# =====================================================
# 4. EXTRACCIÓN DE VENTANA Y MÁSCARA
# =====================================================

def extraer_ventana(datos, x0, y0):

    ny, nx = datos["image"].shape

    ix = int(round(x0))
    iy = int(round(y0))

    xa = max(0, ix - RADIO)
    xb = min(nx, ix + RADIO + 1)

    ya = max(0, iy - RADIO)
    yb = min(ny, iy + RADIO + 1)

    yy, xx = np.mgrid[ya:yb, xa:xb]

    img = datos["image"][ya:yb, xa:xb]
    var = datos["variance"][ya:yb, xa:xb]
    flags = datos["flags"][ya:yb, xa:xb]

    validos = (
        np.isfinite(img)
        & np.isfinite(var)
        & (var > 0)
        & ((flags & BAD_MASK) == 0)
    )

    if validos.sum() < 15:
        raise ValueError(
            f"Solo {validos.sum()} píxeles válidos"
        )

    borde = (
        xa == 0
        or xb == nx
        or ya == 0
        or yb == ny
    )

    return xx, yy, img, var, validos, borde


# =====================================================
# 5. AJUSTE GAUSSIANO Y AJUSTE ePSF
# =====================================================

def ajustar_fuente(datos, x0, y0, tipo="epsf"):

    xx, yy, img, var, validos, borde = (
        extraer_ventana(datos, x0, y0)
    )

    x = xx[validos]
    y = yy[validos]
    z = img[validos]

    error_pix = np.sqrt(var[validos])

    fondo0 = float(np.median(z))

    zona = None
    psf = None

    # ---------------------------------------------
    # Modelo ePSF
    # ---------------------------------------------

    if tipo == "epsf":

        psf, zona, _, _ = seleccionar_epsf(
            datos, x0, y0
        )

        def perfil(cx, cy, sigma=None):
            return np.asarray(
                psf.evaluate(
                    x,
                    y,
                    flux=1.0,
                    x_0=cx,
                    y_0=cy
                )
            )

    # ---------------------------------------------
    # Modelo gaussiano circular
    # ---------------------------------------------

    else:

        def perfil(cx, cy, sigma):

            return np.exp(
                -(
                    (x - cx)**2
                    + (y - cy)**2
                ) / (2 * sigma**2)
            )

    if tipo == "gauss":
        base0 = perfil(x0, y0, 1.2)
    else:
        base0 = perfil(x0, y0)

    if (
        not np.isfinite(base0).all()
        or base0.max() <= 0
    ):
        raise ValueError(
            "Perfil inicial no válido"
        )

    amplitud0 = max(
        float((np.max(z) - fondo0) / base0.max()),
        1e-8
    )

    # Parámetros:
    # amplitud, centro_x, centro_y, fondo
    p0 = [
        amplitud0,
        float(x0),
        float(y0),
        fondo0,
    ]

    inferiores = [
        0,
        x0 - 1.5,
        y0 - 1.5,
        -np.inf,
    ]

    superiores = [
        np.inf,
        x0 + 1.5,
        y0 + 1.5,
        np.inf,
    ]

    # La gaussiana necesita un parámetro extra:
    # sigma espacial.
    if tipo == "gauss":

        p0.append(1.2)

        inferiores.append(0.55)
        superiores.append(3.0)

    # ---------------------------------------------
    # Residuales ponderados
    # ---------------------------------------------

    def residuales(p):

        amp, cx, cy, fondo = p[:4]

        if tipo == "gauss":
            perfil_xy = perfil(
                cx, cy, p[4]
            )
        else:
            perfil_xy = perfil(cx, cy)

        modelo = (
            fondo + amp * perfil_xy
        )

        return (
            (z - modelo) / error_pix
        )

    # ---------------------------------------------
    # Optimización numérica
    # ---------------------------------------------

    ajuste = least_squares(
        residuales,
        x0=p0,
        bounds=(
            inferiores,
            superiores
        ),
        max_nfev=1000,
    )

    if (
        not ajuste.success
        or not np.isfinite(ajuste.x).all()
    ):
        raise ValueError(
            "Optimización no convergente"
        )

    amp, cx, cy, fondo = map(
        float,
        ajuste.x[:4]
    )

    if (
        abs(cx - x0) > 1.48
        or abs(cy - y0) > 1.48
    ):
        raise ValueError(
            "Centroide alcanzó el límite de búsqueda"
        )

    if tipo == "gauss":

        if not (
            0.56 < ajuste.x[4] < 2.99
        ):
            raise ValueError(
                "Sigma gaussiana alcanzó un límite"
            )

    if tipo == "epsf":

        _, zona_final, _, _ = seleccionar_epsf(
            datos,
            cx,
            cy
        )

        if zona_final != zona:
            raise ValueError(
                "El centroide cruza una zona ePSF; "
                "requiere ajuste por zonas"
            )

    # =================================================
    # 6. CHI CUADRADA Y COVARIANZA
    # =================================================

    grados = len(z) - len(ajuste.x)

    if grados <= 0:
        raise ValueError(
            "No hay grados de libertad"
        )

    chi2 = float(
        np.dot(
            ajuste.fun,
            ajuste.fun
        )
    )

    chi2_reducido = chi2 / grados

    J = ajuste.jac

    if (
        np.linalg.matrix_rank(J)
        != J.shape[1]
    ):
        raise ValueError(
            "Jacobiano degenerado"
        )

    # Matriz de covarianza formal.
    informacion = J.T @ J

    cov = np.linalg.inv(
        informacion
    )

    # Inflación exploratoria de errores
    # cuando chi2_reducido > 1.
    # No corrige errores sistemáticos.
    cov *= max(
        1.0,
        chi2_reducido
    )

    cov_xy = cov[
        np.ix_([1, 2], [1, 2])
    ]

    if np.any(
        np.diag(cov_xy) <= 0
    ):
        raise ValueError(
            "Covarianza no válida"
        )

    # ---------------------------------------------
    # Reconstrucción del modelo y residuos
    # ---------------------------------------------

    if tipo == "gauss":
        modelo = fondo + amp * perfil(
            cx,
            cy,
            ajuste.x[4]
        )
    else:
        modelo = fondo + amp * perfil(
            cx,
            cy
        )

    residuo = np.full(
        img.shape,
        np.nan
    )

    residuo[validos] = (
        (z - modelo) / error_pix
    )

    modelo_img = np.full(
        img.shape,
        np.nan
    )

    modelo_img[validos] = modelo

    return {

        "tipo": tipo,

        "x": cx,
        "y": cy,

        "sigma_x": float(
            np.sqrt(cov_xy[0, 0])
        ),

        "sigma_y": float(
            np.sqrt(cov_xy[1, 1])
        ),

        "cov_xy": cov_xy,

        "chi2": chi2,
        "chi2_red": chi2_reducido,

        "dof": grados,
        "n_pix": len(z),

        "zona": zona,

        "amplitud": amp,
        "fondo": fondo,

        "borde": borde,

        "img": img,
        "modelo": modelo_img,
        "residuo": residuo,

        "gauss_sigma": (
            float(ajuste.x[4])
            if tipo == "gauss"
            else np.nan
        ),
    }


# =====================================================
# 7. ASTROMETRÍA Y PROPAGACIÓN DE COVARIANZA
# =====================================================

def astrometria(datos, ajuste):

    wcs = datos["wcs"]

    x = ajuste["x"]
    y = ajuste["y"]

    posicion = wcs.pixel_to_world(x, y)

    # Jacobiano local del WCS mediante
    # diferencias finitas.
    h = 0.01

    posicion_x = wcs.pixel_to_world(
        x + h,
        y
    )

    posicion_y = wcs.pixel_to_world(
        x,
        y + h
    )

    ex, nx = posicion.spherical_offsets_to(
        posicion_x
    )

    ey, ny = posicion.spherical_offsets_to(
        posicion_y
    )

    jac = np.array([
        [
            ex.arcsec / h,
            ey.arcsec / h
        ],
        [
            nx.arcsec / h,
            ny.arcsec / h
        ]
    ])

    # Transformación de covarianza:
    # C_cielo = J * C_pixel * J.T

    cov = (
        jac
        @ ajuste["cov_xy"]
        @ jac.T
    )

    return posicion, cov


# =====================================================
# 8. GRÁFICOS DE RESIDUOS
# =====================================================

def guardar_figura(fuente, resultados):

    fig, axes = plt.subplots(
        2,
        3,
        figsize=(11, 7),
        constrained_layout=True
    )

    for i, epoca in enumerate(
        ["2025", "2026"]
    ):

        r = resultados[epoca]["epsf"]

        elementos = [
            ("Imagen", r["img"]),
            ("Modelo ePSF", r["modelo"]),
            ("Residuo / sigma", r["residuo"]),
        ]

        for j, (nombre, valores) in enumerate(
            elementos
        ):

            ax = axes[i, j]

            if j < 2:

                finitos = r["img"][
                    np.isfinite(r["img"])
                ]

                vmin, vmax = np.percentile(
                    finitos,
                    [5, 99]
                )

                if vmax <= vmin:
                    vmax = vmin + 1

                ax.imshow(
                    valores,
                    origin="lower",
                    cmap="gray",
                    vmin=vmin,
                    vmax=vmax
                )

            else:

                ax.imshow(
                    valores,
                    origin="lower",
                    cmap="coolwarm",
                    vmin=-5,
                    vmax=5
                )

            ax.set_title(
                f"{epoca} — {nombre}"
            )

            ax.set_xlabel(
                "Pixel local X"
            )

            ax.set_ylabel(
                "Pixel local Y"
            )

    ruta = (
        SALIDA
        / f"residuos_epsf_fuente_{fuente}.png"
    )

    fig.savefig(
        ruta,
        dpi=170
    )

    plt.close(fig)

    return ruta


# =====================================================
# 9. PROGRAMA PRINCIPAL
# =====================================================

def main():

    if not CSV_PAREJAS.is_file():
        raise SystemExit(
            "Falta parejas_ordenadas.csv"
        )

    with CSV_PAREJAS.open(
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        parejas = list(
            csv.DictReader(archivo)
        )

    if not parejas:
        raise SystemExit(
            "No hay parejas disponibles"
        )

    pareja = min(
        parejas,
        key=lambda p: float(
            p["desajuste"]
        )
    )

    datos = {

        "2025": leer_datos(
            pareja["archivo_2025"]
        ),

        "2026": leer_datos(
            pareja["archivo_2026"]
        ),
    }

    SALIDA.mkdir(
        exist_ok=True
    )

    print("\n" + "=" * 60)
    print("MORLEY — ePSF INSTRUMENTAL vs GAUSSIANA")
    print("=" * 60)

    print(
        "Pareja:",
        datos["2025"]["obsid"],
        "/",
        datos["2026"]["obsid"]
    )

    print(
        "Desajuste espectral:",
        pareja["desajuste"]
    )

    print(
        "ESTO NO EJECUTA ZOGY "
        "NI CONFIRMA MOVIMIENTO"
    )

    registros = []
    desplazamientos = {}

    # =================================================
    # 10. ANÁLISIS DE CADA FUENTE
    # =================================================

    for nombre, (x0, y0) in FUENTES.items():

        print("\n" + "=" * 55)
        print("FUENTE", nombre)

        ra0, dec0 = (
            datos["2025"]["wcs"]
            .pixel_to_world_values(
                x0,
                y0
            )
        )

        xp, yp = (
            datos["2026"]["wcs"]
            .world_to_pixel_values(
                ra0,
                dec0
            )
        )

        semillas = {

            "2025": (
                x0,
                y0
            ),

            "2026": (
                escalar(xp),
                escalar(yp)
            ),
        }

        resultados = {}

        try:

            for epoca in ("2025", "2026"):

                d = datos[epoca]

                xs, ys = semillas[epoca]

                # Misma región para ambos modelos.
                gauss = ajustar_fuente(
                    d,
                    xs,
                    ys,
                    tipo="gauss"
                )

                epsf = ajustar_fuente(
                    d,
                    xs,
                    ys,
                    tipo="epsf"
                )

                resultados[epoca] = {
                    "gauss": gauss,
                    "epsf": epsf,
                }

                posicion, cov = astrometria(
                    d,
                    epsf
                )

                resultados[epoca]["cielo"] = (
                    posicion,
                    cov
                )

                zona = int(
                    epsf["zona"]
                )

                print(
                    f"\n{epoca}: {d['fecha']}"
                )

                print(
                    f"ePSF zona={zona}, "
                    f"BINX={d['binx'][zona]}, "
                    f"BINY={d['biny'][zona]}"
                )

                print(
                    f"ePSF centro= "
                    f"({epsf['x']:.4f}, "
                    f"{epsf['y']:.4f}) px"
                )

                print(
                    f"ePSF sigma_x="
                    f"{epsf['sigma_x']:.4f}, "
                    f"sigma_y="
                    f"{epsf['sigma_y']:.4f} px"
                )

                print(
                    f"ePSF chi2="
                    f"{epsf['chi2']:.2f}, "
                    f"gl={epsf['dof']}, "
                    f"chi2_red="
                    f"{epsf['chi2_red']:.3f}"
                )

                print(
                    f"Gauss chi2="
                    f"{gauss['chi2']:.2f}, "
                    f"gl={gauss['dof']}, "
                    f"chi2_red="
                    f"{gauss['chi2_red']:.3f}"
                )

                print(
                    "Delta chi2 (Gauss - ePSF) = "
                    f"{gauss['chi2'] - epsf['chi2']:+.2f}"
                )

                print(
                    "Delta centro ePSF-Gauss = "
                    f"({epsf['x']-gauss['x']:+.4f}, "
                    f"{epsf['y']-gauss['y']:+.4f}) px"
                )

                if epsf["borde"]:
                    print(
                        "ADVERTENCIA: ventana toca "
                        "el borde del recorte"
                    )

                registros.append({

                    "fuente": nombre,

                    "epoca": epoca,

                    "obsid": d["obsid"],

                    "centro_x_epsf": epsf["x"],
                    "centro_y_epsf": epsf["y"],

                    "sigma_x_formal_px": (
                        epsf["sigma_x"]
                    ),

                    "sigma_y_formal_px": (
                        epsf["sigma_y"]
                    ),

                    "chi2_epsf": (
                        epsf["chi2"]
                    ),

                    "gl_epsf": (
                        epsf["dof"]
                    ),

                    "chi2_red_epsf": (
                        epsf["chi2_red"]
                    ),

                    "chi2_gauss": (
                        gauss["chi2"]
                    ),

                    "gl_gauss": (
                        gauss["dof"]
                    ),

                    "chi2_red_gauss": (
                        gauss["chi2_red"]
                    ),

                    "epsf_zona": zona,

                    "n_pix": (
                        epsf["n_pix"]
                    ),

                    "borde_recorte": (
                        epsf["borde"]
                    ),

                    "ra_deg": (
                        posicion.ra.deg
                    ),

                    "dec_deg": (
                        posicion.dec.deg
                    ),
                })

            # =================================================
            # 11. DESPLAZAMIENTO APARENTE
            # =================================================

            c1, cov1 = (
                resultados["2025"]["cielo"]
            )

            c2, cov2 = (
                resultados["2026"]["cielo"]
            )

            este, norte = (
                c1.spherical_offsets_to(c2)
            )

            delta = np.array([
                este.arcsec,
                norte.arcsec
            ])

            cov_delta = (
                cov1 + cov2
            )

            sigma_este, sigma_norte = (
                np.sqrt(
                    np.diag(cov_delta)
                )
            )

            desplazamientos[nombre] = (
                delta,
                cov_delta
            )

            print("\nDESPLAZAMIENTO APARENTE")

            print(
                f"Este: {delta[0]:+.4f} "
                f"± {sigma_este:.4f} arcsec"
            )

            print(
                f"Norte: {delta[1]:+.4f} "
                f"± {sigma_norte:.4f} arcsec"
            )

            print(
                "Solo error formal; "
                "NO detección física."
            )

            ruta_figura = guardar_figura(
                nombre,
                resultados
            )

            print(
                "Gráfico:",
                ruta_figura
            )

        except Exception as error:

            print(
                f"ERROR en fuente {nombre}: "
                f"{type(error).__name__}: {error}"
            )

    # =================================================
    # 12. COMPARACIÓN DIFERENCIAL A - B
    # =================================================

    if len(desplazamientos) == 2:

        (a, ca), (b, cb) = (
            desplazamientos["A"],
            desplazamientos["B"]
        )

        diferencia = a - b

        cov = ca + cb

        sigma_e, sigma_n = (
            np.sqrt(
                np.diag(cov)
            )
        )

        print("\nDIFERENCIAL A-B")

        print(
            f"Este: {diferencia[0]:+.4f} "
            f"± {sigma_e:.4f} arcsec"
        )

        print(
            f"Norte: {diferencia[1]:+.4f} "
            f"± {sigma_n:.4f} arcsec"
        )

    # =================================================
    # 13. GUARDAR RESULTADOS
    # =================================================

    if registros:

        ruta = (
            SALIDA
            / "mediciones_epsf_vs_gauss.csv"
        )

        with ruta.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=list(
                    registros[0]
                )
            )

            writer.writeheader()

            writer.writerows(
                registros
            )

        print(
            "\nCSV guardado:",
            ruta
        )

    else:
        raise SystemExit(
            "Ninguna fuente pudo medirse. "
            "Revisa los errores anteriores."
        )

    print(
        "\nIMPORTANTE: la comparación espectral "
        "actual sigue sin validar ZOGY."
    )


if __name__ == "__main__":
    main()
