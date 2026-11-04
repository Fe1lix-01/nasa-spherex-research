"""Práctica 3 MORLEY: espectro exploratorio de M101 desde un mosaico SPHEREx.
Basado en la sección 5 del tutorial de Caltech/IPAC:
https://caltech-ipac.github.io/irsa-tutorials/spherex-mosaic/

Uso desde la raíz de spexpi:
  python labs/science/03_espectro_m101.py labs/science/data/mosaic_cube.fits

Requisitos: numpy, astropy, photutils, matplotlib.
NO es una medición espectrofotométrica científica final.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import cast

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.stats import SigmaClip
from photutils.aperture import (
    ApertureStats,
    CircularAnnulus,
    CircularAperture,
    aperture_photometry,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Espectro exploratorio de M101")
    parser.add_argument("fits_path", type=Path, help="Ruta al mosaico FITS")
    parser.add_argument("--output", type=Path, default=Path("labs/science/outputs/practica03"))
    args = parser.parse_args()

    if not args.fits_path.is_file():
        raise SystemExit(f"No encuentro el FITS: {args.fits_path}")
    args.output.mkdir(parents=True, exist_ok=True)

    # Radio del centro galáctico, y anillo para estimar el fondo.
    r_ap, r_in, r_out = 20, 60, 85

    with fits.open(args.fits_path, memmap=True) as hdul:
        hdul.info()
        # HDUList permite varias clases de extensiones; verificarlas
        # facilita el análisis de tipos de Pylance y evita supuestos incorrectos.
        image_hdu = hdul["IMAGE"]
        nhits_hdu = hdul["NHITS"]
        wave_hdu = hdul["WCS-WAVE"]

        if not isinstance(image_hdu, fits.ImageHDU):
            raise TypeError("IMAGE debe ser una extensión ImageHDU")
        if not isinstance(nhits_hdu, fits.ImageHDU):
            raise TypeError("NHITS debe ser una extensión ImageHDU")
        if not isinstance(wave_hdu, fits.BinTableHDU):
            raise TypeError("WCS-WAVE debe ser una tabla BinTableHDU")

        if image_hdu.data is None or nhits_hdu.data is None or wave_hdu.data is None:
            raise ValueError("El FITS tiene extensiones sin datos")

        cube = image_hdu.data       # (canal, y, x), MJy/sr
        nhits = nhits_hdu.data      # número de contribuciones por píxel
        wave_table = wave_hdu.data
        hdr = image_hdu.header

        n_bands, height, width = cube.shape
        if not (r_ap < r_in < r_out < min(width, height) / 2):
            raise ValueError("El mosaico es demasiado pequeño para los radios escogidos")

        wavelengths = np.asarray(
            wave_table["WAVELENGTHS"][0], dtype=float
        ).reshape(-1)
        plane_ids = np.asarray(
            wave_table["PLANE"][0], dtype=int
        ).reshape(-1)
        if len(wavelengths) != n_bands or len(plane_ids) != n_bands:
            raise ValueError("No coinciden los canales de IMAGE y WCS-WAVE")
        if hdr.get("BUNIT", "").strip().lower() != "mjy/sr":
            raise ValueError(f"Unidad inesperada: {hdr.get('BUNIT')}")

        # Intensidad superficial (MJy/sr) --> flujo por píxel (mJy).
        # Aproximación de píxeles rectangulares pequeños de este mosaico.
        cdelt_x = abs(float(hdr["CDELT1"]))  # grados/píxel
        cdelt_y = abs(float(hdr["CDELT2"]))
        pixel_sr = np.deg2rad(cdelt_x) * np.deg2rad(cdelt_y)
        mjy_per_mjy_sr_pixel = 1e9 * pixel_sr

        # El centro fue fijado sobre M101 al generar este mosaico.
        xy = ((width - 1) / 2, (height - 1) / 2)
        aperture = CircularAperture(xy, r=r_ap)
        background_annulus = CircularAnnulus(xy, r_in=r_in, r_out=r_out)
        sigclip = SigmaClip(sigma=3.0, maxiters=5)
        results = []

        for idx in range(n_bands):
            image = np.asarray(cube[idx], dtype=float) * mjy_per_mjy_sr_pixel
            valid = np.isfinite(image) & (nhits[idx] > 0)
            bad = ~valid

            # Evita sumas sobre zonas sin cobertura.
            area_valid = float(aperture.area_overlap(image, mask=bad))
            if area_valid <= 0:
                net_flux, raw_flux, bkg_level = np.nan, np.nan, np.nan
            else:
                phot_table = aperture_photometry(image, aperture, mask=bad)
                # Astropy devuelve un escalar numérico, aunque sus anotaciones
                # genéricas no permiten inferirlo siempre en Pylance.
                raw_flux = float(cast(float, phot_table["aperture_sum"][0]))
                bkg_level = float(
                    ApertureStats(
                        image, background_annulus, mask=bad, sigma_clip=sigclip
                    ).median
                )
                net_flux = (raw_flux - bkg_level * area_valid) if np.isfinite(bkg_level) else np.nan

            results.append(
                {
                    "plane": int(plane_ids[idx]),
                    "wavelength_um": float(wavelengths[idx]),
                    "raw_flux_mJy": raw_flux,
                    "background_mJy_per_pixel": bkg_level,
                    "net_flux_mJy": net_flux,
                    "valid_aperture_area_pixels": area_valid,
                }
            )

        # Imagen de referencia: canal 63, que ya conoces de la práctica 1.
        channel_63 = int(np.flatnonzero(plane_ids == 63)[0])
        reference = np.asarray(cube[channel_63], dtype=float)

    # Guardar tabla para API/frontend (sin FITS ni JSON gigantescos).
    csv_path = args.output / "espectro_m101.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    # Mostrar dónde se midió el flujo y el fondo.
    fig, ax = plt.subplots(figsize=(7, 6))
    finite = reference[np.isfinite(reference)]
    vmin, vmax = np.percentile(finite, [5, 99.5])
    ax.imshow(reference, origin="lower", cmap="inferno", vmin=vmin, vmax=vmax)
    aperture.plot(ax=ax, color="cyan", lw=2, label="Apertura")
    background_annulus.plot(ax=ax, color="white", lw=1.5, linestyle="--", label="Fondo")
    ax.set(title="M101 — Regiones de fotometría (canal 63)", xlabel="Píxel X", ylabel="Píxel Y")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(args.output / "apertura_m101.png", dpi=160)
    plt.close(fig)

    # Espectro: ordenar por longitud de onda y no conectar huecos sin datos.
    x = np.array([r["wavelength_um"] for r in results])
    y = np.array([r["net_flux_mJy"] for r in results])
    order = np.argsort(x)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x[order], y[order], "o-", markersize=3, linewidth=0.8)
    ax.axvline(3.3, color="gray", ls="--", lw=1, label="PAH ~3.3 µm (referencia)")
    ax.set(xlabel="Longitud de onda (µm)", ylabel="Flujo neto aproximado (mJy)",
           title="M101 — Espectro exploratorio (apertura circular)")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(args.output / "espectro_m101.png", dpi=160)
    plt.close(fig)

    print(f"\nCubos: {n_bands} bandas, {width} × {height} píxeles")
    print(f"Canal 63: {wavelengths[channel_63]:.4f} µm")
    print(f"Conversión: 1 MJy/sr equivale a {mjy_per_mjy_sr_pixel:.5f} mJy/píxel")
    print(f"Bandas con medición neta válida: {np.isfinite(y).sum()}/{n_bands}")
    print(f"Guardado en: {args.output.resolve()}")
    print("IMPORTANTE: quick-look; no incluye incertidumbres calibradas ni interpretación de FLAGS.")


if __name__ == "__main__":
    main()
