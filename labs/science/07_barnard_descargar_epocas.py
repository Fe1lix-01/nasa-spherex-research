"""Práctica 7: descargar varias épocas reales de la estrella de Barnard y convertirlas a PNG.

Usa el CSV que generó 06_barnard_consultar_irsa.py (lista de observaciones reales de
SPHEREx que cubren la posición de Barnard). De esas filas, elige automáticamente varias
observaciones repartidas lo más lejos posible unas de otras en el tiempo (para que el
movimiento se note al máximo), pide a IRSA el RECORTE pequeño (no el archivo completo)
alrededor de la estrella, y convierte cada recorte FITS a una imagen PNG lista para el visor.

Uso:
    python 07_barnard_descargar_epocas.py              # 5 épocas (por defecto)
    python 07_barnard_descargar_epocas.py --epochs 3    # elige cuántas quieres

Qué escribe:
- outputs/practica07_barnard/eN.fits   (el recorte real descargado)
- outputs/practica07_barnard/eN.png    (la imagen convertida, lista para el frontend)
- outputs/practica07_barnard/manifest.json  (fecha, posición y campo de visión de cada época)
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import requests
from astropy.io import fits
from astropy.time import Time
from astropy.visualization import AsinhStretch, PercentileInterval
from astropy.wcs import WCS

# Centro aproximado de Barnard, el mismo que usa la práctica 6.
RA = 269.44627
DEC = 4.76820

# Campo de visión del recorte, en grados. 0.08° ~ 288 segundos de arco: da un poco de
# contexto alrededor de la estrella (otras fuentes débiles) sin que el movimiento, que es de
# unos 11 segundos de arco, se pierda dentro de un cuadro demasiado grande.
CUTOUT_SIZE_DEG = 0.08

# A cuántos píxeles se agranda el PNG final. El recorte real trae pocos píxeles (SPHEREx
# mide ~6.2 segundos de arco por píxel), así que se amplía con suavizado para que en
# pantalla no se vea cuadriculado. No agrega detalle: solo mejora cómo se ve.
PNG_SIZE_PX = 512


def load_observations(csv_path: Path) -> list[dict]:
    with csv_path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pick_spread_epochs(observations: list[dict], n: int) -> list[dict]:
    """Elige n observaciones del CSV, repartidas lo más lejos posible en el tiempo.

    Siempre incluye la primera y la última (el mayor salto posible), y va agregando,
    una por una, la fecha que quede más lejos de las ya elegidas. Así, con pocas épocas
    se cubre todo el rango disponible y el movimiento entre ellas es el más notorio.
    """
    rows = sorted(observations, key=lambda row: row["observation_mjd"])
    n = max(1, min(n, len(rows)))
    if n == 1:
        return [rows[len(rows) // 2]]

    mjds = [float(row["observation_mjd"]) for row in rows]
    chosen = {0, len(rows) - 1}

    while len(chosen) < n:
        best_i, best_gap = None, -1.0
        for i in range(len(rows)):
            if i in chosen:
                continue
            gap = min(abs(mjds[i] - mjds[c]) for c in chosen)
            if gap > best_gap:
                best_gap, best_i = gap, i
        chosen.add(best_i)

    return [rows[i] for i in sorted(chosen)]


def cutout_url(artifact_uri: str) -> str:
    return f"https://irsa.ipac.caltech.edu/{artifact_uri}?center={RA},{DEC}d&size={CUTOUT_SIZE_DEG}"


def download_cutout(url: str, dest: Path, attempts: int = 8) -> None:
    """Descarga el recorte. IRSA a veces responde 503 (ocupado); se reintenta con espera."""
    import time

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, timeout=(15, 120))
            response.raise_for_status()
            dest.write_bytes(response.content)
            return
        except requests.exceptions.HTTPError as error:
            last_error = error
            status = error.response.status_code if error.response is not None else None
            if status in (503, 429) and attempt < attempts:
                wait = min(10 * attempt, 60)
                print(f"  IRSA respondió {status} (ocupado); reintento {attempt}/{attempts} en {wait}s...")
                time.sleep(wait)
                continue
            raise
    if last_error:
        raise last_error


def fits_to_png(fits_path: Path, png_path: Path) -> tuple[float, float, float]:
    """Convierte la extensión IMAGE a PNG y regresa (ra_centro, dec_centro, fov_deg)."""
    with fits.open(fits_path) as hdul:
        image_hdu = hdul["IMAGE"]
        image = np.asarray(image_hdu.data, dtype=float)
        header = image_hdu.header

        # Centro y campo de visión reales, leídos del WCS del recorte (no los que pedimos:
        # IRSA puede ajustar el recorte al tamaño de píxel real de SPHEREx).
        wcs = WCS(header)
        ny, nx = image.shape
        ra_center, dec_center = wcs.all_pix2world(nx / 2, ny / 2, 0)
        # Tamaño angular aproximado del recorte (asumiendo píxeles cuadrados).
        scale_deg_per_px = abs(wcs.pixel_scale_matrix[0, 0])
        fov_deg = scale_deg_per_px * max(nx, ny)

        # Estiramiento del contraste. Se recorta el 99.5 % central de los valores y luego se
        # aplica asinh con un parámetro pequeño: así las fuentes débiles de alrededor se ven,
        # sin que la estrella brillante se "queme" y tape todo.
        # NaN (píxeles sin cobertura) se pintan en negro.
        finite = np.isfinite(image)
        interval = PercentileInterval(99.5)
        vmin, vmax = interval.get_limits(image[finite])
        stretch = AsinhStretch(a=0.02)

        norm = np.zeros_like(image)
        norm[finite] = np.clip((image[finite] - vmin) / (vmax - vmin), 0, 1)
        norm[finite] = stretch(norm[finite])

        from PIL import Image

        pixels = (np.clip(norm, 0, 1) * 255).astype(np.uint8)
        picture = Image.fromarray(pixels, mode="L")
        # Se amplía con suavizado (Lanczos) para que en pantalla no se vea cuadriculado.
        picture = picture.resize((PNG_SIZE_PX, PNG_SIZE_PX), Image.LANCZOS)
        picture.save(png_path)

        return float(ra_center), float(dec_center), float(fov_deg)


def main() -> None:
    parser = argparse.ArgumentParser(description="Descargar épocas reales de Barnard")
    parser.add_argument("--epochs", type=int, default=5, help="Cuántas épocas elegir (por defecto 5)")
    parser.add_argument(
        "--csv",
        default=None,
        help="Ruta del CSV de observaciones (por defecto, el de la práctica 6)",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    csv_path = Path(args.csv) if args.csv else base_dir / "outputs" / "practica06_barnard" / "barnard_D2.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"No encuentro el CSV de la práctica 6. Corre primero 06_barnard_consultar_irsa.py.\n{csv_path}"
        )

    output_dir = base_dir / "outputs" / "practica07_barnard"
    output_dir.mkdir(parents=True, exist_ok=True)

    observations = load_observations(csv_path)
    chosen = pick_spread_epochs(observations, args.epochs)

    span_days = Time(chosen[-1]["observation_utc"]) - Time(chosen[0]["observation_utc"])
    print(f"Observaciones totales en el CSV: {len(observations)}")
    print(f"Épocas elegidas: {len(chosen)} (abarcan {span_days.to('day').value:.1f} días)")

    manifest = []

    for i, row in enumerate(chosen, start=1):
        print(f"\nÉpoca {i}: {row['observation_utc']}")

        fits_path = output_dir / f"e{i}.fits"
        png_path = output_dir / f"e{i}.png"

        if fits_path.exists() and png_path.exists():
            print("  Ya estaba descargada, se usa la que ya tienes.")
        else:
            url = cutout_url(row["artifact_uri"])
            print("Descargando recorte...")
            try:
                download_cutout(url, fits_path)
            except Exception as error:
                print(f"  No se pudo descargar esta época, se omite: {error}")
                continue
            print(f"  FITS guardado: {fits_path} ({fits_path.stat().st_size / 1024:.1f} KiB)")

        ra_center, dec_center, fov_deg = fits_to_png(fits_path, png_path)
        print(f"  PNG guardado: {png_path}")
        print(f"  Centro real: RA={ra_center:.5f}, Dec={dec_center:.5f}, FOV={fov_deg:.4f}°")

        manifest.append(
            {
                "epochId": f"e{i}",
                "observedAt": row["observation_utc"][:10],
                "observedAtUtc": row["observation_utc"],
                "ra": ra_center,
                "dec": dec_center,
                "fovDeg": fov_deg,
                "imageFile": png_path.name,
            }
        )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nManifiesto guardado en: {manifest_path}")


if __name__ == "__main__":
    main()
