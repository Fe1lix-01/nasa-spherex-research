
import csv
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from astropy.io import fits
from astropy.wcs import WCS

# Posiciones aproximadas observadas en la imagen de 2025
FUENTES = {
    "A": (22.0, 6.0),
    "B": (15.0, 4.0),
}

# SOURCE (bit 21) está permitido
BITS_MALOS = [
    0, 1, 2, 6, 7, 9, 10, 11,
    14, 15, 17, 19, 20, 22
]
BAD_MASK = sum(1 << bit for bit in BITS_MALOS)


def cargar_fits(ruta):
    with fits.open(Path(ruta)) as hdul:
        return {
            "image": hdul["IMAGE"].data.astype(float).copy(),
            "variance": hdul["VARIANCE"].data.astype(float).copy(),
            "flags": hdul["FLAGS"].data.astype(np.int64).copy(),
            "wcs": WCS(
                hdul["IMAGE"].header,
                fobj=hdul
            ).celestial,
            "date": hdul["IMAGE"].header.get("DATE-OBS"),
        }


def medir_centro(datos, x0, y0, radio=3):
    """
    Ajuste preliminar de gaussiana circular 2D
    con fondo constante y pesos por varianza.

    No sustituye un ajuste ePSF instrumental.
    """

    imagen = datos["image"]
    varianza = datos["variance"]
    flags = datos["flags"]

    ny, nx = imagen.shape

    ix, iy = round(x0), round(y0)

    xa = max(0, ix - radio)
    xb = min(nx, ix + radio + 1)

    ya = max(0, iy - radio)
    yb = min(ny, iy + radio + 1)

    yy, xx = np.mgrid[ya:yb, xa:xb]

    z = imagen[ya:yb, xa:xb]
    v = varianza[ya:yb, xa:xb]
    f = flags[ya:yb, xa:xb]

    validos = (
        np.isfinite(z)
        & np.isfinite(v)
        & (v > 0)
        & ((f & BAD_MASK) == 0)
    )

    if np.count_nonzero(validos) < 15:
        raise ValueError(
            "No hay suficientes píxeles válidos"
        )

    x = xx[validos].astype(float)
    y = yy[validos].astype(float)
    valores = z[validos]
    errores = np.sqrt(v[validos])

    fondo = float(np.median(valores))
    amplitud = max(
        float(np.max(valores) - fondo),
        1e-6
    )

    def residuales(p):
        amp, cx, cy, sigma, bg = p

        modelo = (
            bg
            + amp * np.exp(
                -(
                    (x - cx) ** 2
                    + (y - cy) ** 2
                ) / (2 * sigma ** 2)
            )
        )

        return (valores - modelo) / errores

    resultado = least_squares(
        residuales,
        x0=[
            amplitud,
            x0,
            y0,
            1.2,
            fondo,
        ],
        bounds=(
            [
                0,
                x0 - 1.5,
                y0 - 1.5,
                0.55,
                -np.inf,
            ],
            [
                np.inf,
                x0 + 1.5,
                y0 + 1.5,
                3.0,
                np.inf,
            ],
        ),
        max_nfev=500,
    )

    if not resultado.success:
        raise ValueError("El ajuste no convergió")

    amp, cx, cy, sigma, bg = resultado.x

    if (
        abs(cx - x0) >= 1.49
        or abs(cy - y0) >= 1.49
    ):
        raise ValueError(
            "El centro alcanzó el límite del ajuste"
        )

    return float(cx), float(cy)


def main():
    with open(
        "parejas_ordenadas.csv",
        encoding="utf-8-sig"
    ) as f:
        parejas = list(csv.DictReader(f))

    if not parejas:
        raise SystemExit("No hay parejas")

    mejor = min(
        parejas,
        key=lambda p: float(p["desajuste"])
    )

    a = cargar_fits(mejor["archivo_2025"])
    b = cargar_fits(mejor["archivo_2026"])

    print("\nMORLEY — ASTROMETRÍA OBSERVACIONAL")
    print("2025:", a["date"])
    print("2026:", b["date"])
    print("Desajuste espectral:", mejor["desajuste"])

    desplazamientos = {}

    for nombre, (x0, y0) in FUENTES.items():
        try:
            # Ajuste independiente sobre FITS 2025
            x1, y1 = medir_centro(a, x0, y0)

            sky1 = a["wcs"].pixel_to_world(x1, y1)

            # Usar la posición aproximada para localizar
            # la fuente en 2026, no para fijar su centro.
            ra0, dec0 = a["wcs"].pixel_to_world_values(
                x0, y0
            )

            xp, yp = b["wcs"].world_to_pixel_values(
                ra0, dec0
            )

            xp = float(np.asarray(xp).item())
            yp = float(np.asarray(yp).item())

            # Ajuste independiente sobre FITS 2026
            x2, y2 = medir_centro(b, xp, yp)

            sky2 = b["wcs"].pixel_to_world(x2, y2)

            este, norte = sky1.spherical_offsets_to(sky2)

            de = float(este.arcsec)
            dn = float(norte.arcsec)

            desplazamientos[nombre] = (de, dn)

            print("\n" + "=" * 45)
            print("FUENTE", nombre)

            print(
                f"2025 píxeles: ({x1:.4f}, {y1:.4f})"
            )
            print(
                f"2026 píxeles: ({x2:.4f}, {y2:.4f})"
            )

            print(
                f"RA 2025: {sky1.ra.deg:.8f}"
            )
            print(
                f"Dec 2025: {sky1.dec.deg:.8f}"
            )
            print(
                f"RA 2026: {sky2.ra.deg:.8f}"
            )
            print(
                f"Dec 2026: {sky2.dec.deg:.8f}"
            )

            print(f"Desplazamiento Este: {de:.4f} arcsec")
            print(f"Desplazamiento Norte: {dn:.4f} arcsec")
            print(
                "Magnitud aparente:",
                round(np.hypot(de, dn), 4),
                "arcsec"
            )

        except Exception as error:
            print(
                f"No se pudo medir {nombre}: {error}"
            )

    if len(desplazamientos) == 2:
        a_e, a_n = desplazamientos["A"]
        b_e, b_n = desplazamientos["B"]

        print("\n" + "=" * 45)
        print("COMPARACIÓN DIFERENCIAL A - B")

        print(
            "Delta Este:",
            round(a_e - b_e, 4),
            "arcsec"
        )
        print(
            "Delta Norte:",
            round(a_n - b_n, 4),
            "arcsec"
        )

        print(
            "Esta diferencia NO demuestra movimiento "
            "físico sin incertidumbres ni referencia externa."
        )


if __name__ == "__main__":
    main()
