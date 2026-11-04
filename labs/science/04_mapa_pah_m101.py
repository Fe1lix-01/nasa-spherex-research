"""Práctica 4 — Mapa exploratorio del exceso espectral a 3.3 µm en M101.

Basado en la sección 6 del tutorial de mosaicos SPHEREx de Caltech/IPAC:
https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic/

Uso desde la raíz del repositorio:
    python labs/science/04_mapa_pah_m101.py labs/science/data/mosaic_cube.fits --show

Este mapa NO es una medición científica calibrada de PAH ni un mapa temporal.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

# Según la documentación de IRSA: bit 1 = OVERFLOW, bit 19 = OUTLIER.
# No descartamos SOURCE (bit 21): es una marca de fuente conocida, no de error.
BAD_BITS = (1 << 1)
FEATURE_PLANE = 63  # FITS/IRSA numera las bandas a partir de 1.
CONTINUUM_PLANES = (61, 62, 64, 65)


def load_plane(hdul: fits.HDUList, name: str, plane_id: int) -> np.ndarray:
    """Obtiene una capa 2D como copia numérica, sin modificar el FITS."""
    hdu = hdul[name]
    if not isinstance(hdu, (fits.ImageHDU, fits.PrimaryHDU)) or hdu.data is None:
        raise ValueError(f"La extensión {name} no es una imagen con datos.")
    cube = np.asarray(hdu.data)
    if cube.ndim != 3 or not 1 <= plane_id <= cube.shape[0]:
        raise ValueError(f"Dimensiones inesperadas en {name}: {cube.shape}")
    return np.asarray(cube[plane_id - 1]).copy()


def safe_percentile(image: np.ndarray, p_low: float, p_high: float) -> tuple[float, float]:
    good = image[np.isfinite(image)]
    if good.size == 0:
        raise ValueError("No quedaron píxeles válidos después de aplicar las máscaras.")
    low, high = np.percentile(good, [p_low, p_high])
    if low == high:
        high = low + 1e-6
    return float(low), float(high)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mapa espectral exploratorio PAH M101")
    parser.add_argument(
        "fits_path", nargs="?", type=Path,
        default=Path("labs/science/data/mosaic_cube.fits"),
        help="Ruta al mosaico FITS obtenido de IRSA",
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path("labs/science/outputs/practica04"),
        help="Carpeta donde se guardarán resultados",
    )
    parser.add_argument("--show", action="store_true", help="Mostrar ventanas Matplotlib")
    parser.add_argument("--exclude-outliers", action="store_true",
                        help="Excluir píxeles OUTLIER (bit 19), puede generar huecos visibles")
    args = parser.parse_args()

    if not args.fits_path.is_file():
        raise SystemExit(f"No se encontró el FITS: {args.fits_path}")
    args.out.mkdir(parents=True, exist_ok=True)

    ids = (FEATURE_PLANE, *CONTINUUM_PLANES)
    with fits.open(args.fits_path, memmap=True) as hdul:
        wave_hdu = hdul["WCS-WAVE"]
        if not isinstance(wave_hdu, fits.BinTableHDU) or wave_hdu.data is None:
            raise ValueError("No existe tabla válida WCS-WAVE en este FITS.")
        wave_table = wave_hdu.data
        # Aplanar la dimensión extra de las columnas vectoriales FITS.
        plane_numbers = np.asarray(wave_table["PLANE"][0], dtype=int).reshape(-1)
        wavelengths = np.asarray(wave_table["WAVELENGTHS"][0], dtype=float).reshape(-1)
        if plane_numbers.size != wavelengths.size:
            raise ValueError("PLANE y WAVELENGTHS tienen tamaños diferentes")
        wavelength_by_plane = {
            int(p): float(w) for p, w in zip(plane_numbers, wavelengths)
        }
        if not all(p in wavelength_by_plane for p in ids):
            raise ValueError("Faltan canales esperados en WCS-WAVE")

        image_hdu = hdul["IMAGE"]
        if not isinstance(image_hdu, fits.ImageHDU):
            raise ValueError("Se esperaba una imagen en extensión IMAGE.")
        unit = image_hdu.header.get("BUNIT", "MJy/sr").strip()
        print(f"Archivo: {args.fits_path}")
        print(f"Unidades originales: {unit}")

        images: dict[int, np.ndarray] = {}
        valid_masks: dict[int, np.ndarray] = {}
        for plane_id in ids:
            img = load_plane(hdul, "IMAGE", plane_id).astype(np.float64)
            hits = load_plane(hdul, "NHITS", plane_id)
            flags = load_plane(hdul, "FLAGS", plane_id)
            exclude_bits = BAD_BITS | ((1 << 19) if args.exclude_outliers else 0)
            good = np.isfinite(img) & (hits > 0) & ((flags & exclude_bits) == 0)
            img[~good] = np.nan
            images[plane_id] = img
            valid_masks[plane_id] = good
            print(
                f"Canal {plane_id:3d} | {wavelength_by_plane[plane_id]:.3f} µm "
                f"| píxeles válidos: {np.count_nonzero(good):,} / {img.size:,}"
            )

    feature = images[FEATURE_PLANE]
    continuum_stack = np.stack([images[p] for p in CONTINUUM_PLANES], axis=0)
    # La mediana es robusta ante un valor aislado, pero NO corrige PSF ni calibración.
    continuum = np.ma.median(
        np.ma.masked_invalid(continuum_stack), axis=0
    ).filled(np.nan)
    valid_count = np.sum(np.isfinite(continuum_stack), axis=0)
    valid = np.isfinite(feature) & (valid_count >= 3) & np.isfinite(continuum)
    residual = np.where(valid, feature - continuum, np.nan)

    if not np.any(valid):
        raise SystemExit("No se encontraron píxeles con cobertura adecuada.")

    print(f"Píxeles válidos para el mapa final: {np.count_nonzero(valid):,}")
    print("Mediana del exceso (MJy/sr):", float(np.nanmedian(residual)))
    print("Fracción de píxeles con exceso positivo:", float(np.mean(residual[valid] > 0)))

    # Comparación con la misma escala de color para FEATURE y CONTINUUM.
    common_data = np.concatenate([feature[valid], continuum[valid]])
    vmin, vmax = map(float, np.percentile(common_data, [5, 99.5]))
    limit = float(np.nanpercentile(np.abs(residual), 99))
    limit = max(limit, 1e-6)

    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)
    for ax, img, title in zip(
        axes[:2],
        [feature, continuum],
        ["Canal 63 — 3.293 µm", "Continuo estimado — canales 61,62,64,65"],
    ):
        im = ax.imshow(img, origin="lower", cmap="inferno", vmin=vmin, vmax=vmax)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Píxel X")
        ax.set_ylabel("Píxel Y")
    fig.colorbar(im, ax=axes[:2].tolist(), shrink=0.78, label=unit)

    diff_im = axes[2].imshow(
        residual, origin="lower", cmap="RdBu_r", vmin=-limit, vmax=limit
    )
    axes[2].set_title("Exceso espectral a 3.3 µm (exploratorio)", fontsize=10)
    axes[2].set_xlabel("Píxel X")
    axes[2].set_ylabel("Píxel Y")
    fig.colorbar(diff_im, ax=axes[2], shrink=0.78, label=unit)
    fig.suptitle("M101 · SPHEREx · estimación del exceso espectral", fontsize=14)
    comparison_path = args.out / "comparacion_bandas_m101.png"
    fig.savefig(comparison_path, dpi=170)

    fig2, ax2 = plt.subplots(figsize=(7, 6))
    # Mapa secuencial para comparar con el tutorial; los valores negativos se mantienen
    # en el archivo numérico y no deben interpretarse como 'no hay PAH'.
    low, high = safe_percentile(residual, 5, 99.5)
    p = ax2.imshow(residual, cmap="inferno", origin="lower", vmin=low, vmax=high)
    ax2.set(title="M101 — Exceso cercano a 3.3 µm", xlabel="Píxel X", ylabel="Píxel Y")
    fig2.colorbar(p, ax=ax2, label=unit)
    fig2.tight_layout()
    map_path = args.out / "mapa_pah_m101.png"
    fig2.savefig(map_path, dpi=170)

    # Los datos permanecen numéricos: útil para prácticas posteriores en API/frontend.
    numeric_path = args.out / "mapa_pah_m101.npy"
    np.save(numeric_path, residual.astype(np.float32))
    metadata = {
        "source_file": args.fits_path.name,
        "method": "feature minus median of nearby continuum planes; quick-look only",
        "feature_plane": FEATURE_PLANE,
        "feature_wavelength_um": wavelength_by_plane[FEATURE_PLANE],
        "continuum_planes": list(CONTINUUM_PLANES),
        "continuum_wavelengths_um": [wavelength_by_plane[p] for p in CONTINUUM_PLANES],
        "shape_yx": list(residual.shape),
        "units": unit,
        "excluded_flag_bits": [1, 19] if args.exclude_outliers else [1],
        "outliers_excluded": args.exclude_outliers,
        "min_valid_continuum_planes": 3,
        "valid_pixel_count": int(np.count_nonzero(valid)),
        "caution": "Not a calibrated PAH measurement. Not a time-domain image difference.",
    }
    (args.out / "metadatos_m101.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\nArchivos generados:")
    for path in [comparison_path, map_path, numeric_path, args.out / "metadatos_m101.json"]:
        print(" -", path)
    if args.show:
        plt.show()
    else:
        plt.close("all")


if __name__ == "__main__":
    main()