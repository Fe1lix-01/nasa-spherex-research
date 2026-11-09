from pathlib import Path

import numpy as np
from astropy.io import fits

BASE = Path(__file__).resolve().parent

archivo = (
    BASE
    / "outputs/practica08_barnard"
    / "cutout_2026W12_1A_0311_3.fits"
)

# Cada número indica una condición registrada
# en un bit concreto del entero FLAGS.
FLAG_BITS = {
    "TRANSIENT": 0,
    "OVERFLOW": 1,
    "SUR_ERROR": 2,
    "NONFUNC": 6,
    "DICHROIC": 7,
    "MISSING_DATA": 9,
    "HOT": 10,
    "COLD": 11,
    "FULLSAMPLE": 12,
    "PHANMISS": 14,
    "NONLINEAR": 15,
    "PERSIST": 17,
    "OUTLIER": 19,
    "SOURCE": 21,
}

with fits.open(archivo) as hdul:
    image = np.asarray(hdul["IMAGE"].data)
    flags = np.asarray(
        hdul["FLAGS"].data, dtype=np.int64
    )
    variance = np.asarray(
        hdul["VARIANCE"].data
    )

    print("Forma:", image.shape)
    print("Píxeles totales:", image.size)

    print("\nINDICADORES ACTIVOS")

    for name, bit in FLAG_BITS.items():
        mask = (flags & (1 << bit)) != 0
        count = int(np.count_nonzero(mask))

        if count:
            print(f"{name:15s}: {count:3d}")

    print("\nVALORES DE FLAGS MÁS FRECUENTES")

    values, counts = np.unique(
        flags, return_counts=True
    )

    order = np.argsort(counts)[::-1]

    for i in order[:10]:
        print(
            f"Valor: {int(values[i]):12d} "
            f"| píxeles: {int(counts[i])}"
        )

    # Primera máscara de calidad educativa.
    # No equivale a la máscara científica
    # definitiva para fotometría SPHEREx.
    bad_names = [
        "TRANSIENT",
        "OVERFLOW",
        "SUR_ERROR",
        "NONFUNC",
        "DICHROIC",
        "MISSING_DATA",
        "HOT",
        "COLD",
        "PHANMISS",
        "NONLINEAR",
        "PERSIST",
        "OUTLIER",
    ]

    bad_bits = 0

    for name in bad_names:
        bad_bits |= 1 << FLAG_BITS[name]

    good = (
        np.isfinite(image)
        & np.isfinite(variance)
        & (variance > 0)
        & ((flags & bad_bits) == 0)
    )

    print("\nRESUMEN DE CALIDAD")
    print("Píxeles útiles preliminares:", good.sum())
    print("Píxeles excluidos:", good.size - good.sum())

    if np.any(good):
        sigma = np.sqrt(variance[good])

        print(
            "Mediana de sigma:",
            float(np.median(sigma)),
            "MJy/sr"
        )
