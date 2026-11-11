#
import argparse
import csv
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS


# 1. Configuración de nuestro experimento
RA = 269.44627
DEC = 4.76820

OBS_ID_DEFAULT = "2026W12_1A_0311_3"
MAX_BYTES = 100 * 1024 * 1024 #Definir el tamaño y peso maximo de la imagen

SCIENCE_DIR = Path(__file__).resolve().parent

CATALOG = (
    SCIENCE_DIR
    / "outputs/practica07_barnard/barnard_observaciones_D2.csv"
)

OUTPUT = SCIENCE_DIR / "outputs/practica08_barnard"


# 2. Buscar una observación en nuestro CSV
def find_observation(obs_id):
    if not CATALOG.exists():
        raise SystemExit(f"Falta el CSV: {CATALOG}")

    with CATALOG.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    matches = [
        row for row in rows
        if row["obs_id"] == obs_id
    ]

    if len(matches) != 1:
        raise SystemExit(
            f"Se esperaba un registro para {obs_id}; "
            f"se encontraron {len(matches)}."
        )

    return matches[0]


# 3. Descargar únicamente el recorte solicitado
def download_cutout(url, destination):
    if destination.exists():
        print("El FITS ya existe:", destination)
        return

    tmp = destination.with_suffix(".fits.part")

    try:
        request = Request(
            url,
            headers={"User-Agent": "MORLEY-training/1.0"}
        )

        with urlopen(request, timeout=120) as response:
            declared = int(
                response.headers.get("Content-Length", "0")
            )

            if declared > MAX_BYTES:
                raise ValueError(
                    "El servidor anunció un archivo demasiado grande."
                )

            total = 0

            with tmp.open("wb") as file:
                while True:
                    chunk = response.read(1024 * 1024)

                    if not chunk:
                        break

                    total += len(chunk)

                    if total > MAX_BYTES:
                        raise ValueError(
                            "La descarga superó 100 MB. "
                            "Revisa los parámetros del recorte."
                        )

                    file.write(chunk)

        # Comprobación básica de la cabecera FITS
        with tmp.open("rb") as file:
            if file.read(9) != b"SIMPLE  =":
                raise ValueError(
                    "La respuesta no parece ser un FITS."
                )

        tmp.replace(destination)

        print(
            f"Descarga completada: "
            f"{total / 1024**2:.2f} MB"
        )

    except (
        HTTPError,
        URLError,
        TimeoutError,
        ValueError
    ) as error:
        tmp.unlink(missing_ok=True)

        raise SystemExit(
            f"No se pudo descargar el recorte: {error}"
        ) from error


# 4. Programa principal
def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--obs-id",
        default=OBS_ID_DEFAULT
    )

    parser.add_argument(
        "--size-arcsec",
        type=float,
        default=90.0
    )

    parser.add_argument(
        "--show",
        action="store_true"
    )

    args = parser.parse_args()

    if not 30 <= args.size_arcsec <= 240:
        parser.error(
            "El tamaño debe estar entre 30 y 240 arcsec."
        )

    obs = find_observation(args.obs_id)

    base_url = obs["access_url"].strip()

    parsed = urlsplit(base_url)

    if (
        parsed.scheme != "https"
        or parsed.hostname != "irsa.ipac.caltech.edu"
        or not parsed.path.endswith(".fits")
    ):
        raise SystemExit("URL FITS de IRSA no válida.")

    # El servicio IRSA recibe el tamaño en grados
    size_deg = args.size_arcsec / 3600.0

    separator = "&" if parsed.query else "?"

    url = (
        f"{base_url}{separator}"
        f"center={RA:.8f},{DEC:.8f}"
        f"&size={size_deg:.8f}"
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)

    destination = (
        OUTPUT / f"cutout_{args.obs_id}.fits"
    )

    print("Observación:", args.obs_id)
    print("Fecha UTC:", obs["date_utc"])
    print("Release:", obs["release"])
    print(f"Tamaño: {args.size_arcsec} arcsec")
    print("URL de recorte:", url)

    download_cutout(url, destination)

    # 5. Abrir e inspeccionar las extensiones
    print("\nEXTENSIONES DEL FITS")

    with fits.open(destination, memmap=False) as hdul:
        hdul.info()

        if "IMAGE" not in hdul:
            raise SystemExit(
                "No se encontró la extensión IMAGE."
            )

        hdu = hdul["IMAGE"]

        image = np.asarray(hdu.data, dtype=float)

        if image.ndim != 2 or not np.isfinite(image).any():
            raise SystemExit(
                "IMAGE no contiene datos 2D válidos."
            )

        print("\nMETADATOS DE IMAGE")

        for keyword in [
            "BUNIT",
            "DETECTOR",
            "OBSID",
            "DATE",
            "PSF_FWHM"
        ]:
            value = hdu.header.get(
                keyword, "No indicado"
            )
            print(f"{keyword}: {value}")

        version = hdul[0].header.get(
            "VERSION", "No indicada"
        )

        print("VERSION:", version)
        print("Forma de la matriz:", image.shape)

        valid_pixels = np.isfinite(image).sum()

        print(
            "Píxeles finitos:",
            valid_pixels,
            "/",
            image.size
        )

        if "FLAGS" in hdul:
            flags = np.asarray(hdul["FLAGS"].data)

            print(
                "Píxeles con flags distintos de cero:",
                int(np.count_nonzero(flags))
            )

        if "VARIANCE" in hdul:
            print(
                "Forma de VARIANCE:",
                hdul["VARIANCE"].data.shape
            )

        # 6. Coordenadas celestes -> coordenadas de píxel
        x = y = None

        try:
            target = SkyCoord(
                RA * u.deg,
                DEC * u.deg,
                frame="icrs"
            )

            spatial_wcs = WCS(hdu.header)

            x, y = spatial_wcs.world_to_pixel(target)

            print(
                f"Centro de búsqueda: "
                f"x={x:.2f}, y={y:.2f}"
            )

        except Exception as error:
            print("No se pudo calcular WCS:", error)

        # 7. Longitud de onda en el centro buscado
        if x is not None and y is not None:
            try:
                spectral_wcs = WCS(
                    hdu.header,
                    fobj=hdul,
                    key="W"
                )

                spectral_wcs.sip = None

                wavelength, bandwidth = (
                    spectral_wcs.pixel_to_world(x, y)
                )

                print(
                    "Longitud de onda:",
                    f"{wavelength.to_value(u.um):.4f} µm"
                )

                print(
                    "Ancho de banda:",
                    f"{bandwidth.to_value(u.um):.4f} µm"
                )

            except Exception as error:
                print(
                    "No se pudo calcular el WCS espectral:",
                    error
                )

    # 8. Generar una imagen de visualización
    valid = image[np.isfinite(image)]

    vmin, vmax = np.percentile(
        valid, [5, 99.5]
    )

    if vmax <= vmin:
        vmax = vmin + 1.0

    fig, ax = plt.subplots(figsize=(6, 6))

    ax.imshow(
        image,
        origin="lower",
        cmap="gray",
        vmin=vmin,
        vmax=vmax
    )

    # La cruz marca el centro consultado, no una
    # detección confirmada de Barnard.
    if (
        x is not None
        and y is not None
        and 0 <= x < image.shape[1]
        and 0 <= y < image.shape[0]
    ):
        ax.plot(
            x,
            y,
            marker="+",
            color="cyan",
            markersize=12,
            markeredgewidth=1.5
        )

    ax.set_title(
        f"SPHEREx D2 | {obs['date_utc'][:10]}"
    )

    ax.set_xlabel("Píxel X")
    ax.set_ylabel("Píxel Y")

    fig.tight_layout()

    png_path = (
        OUTPUT / f"imagen_{args.obs_id}.png"
    )

    fig.savefig(png_path, dpi=180)

    print("\nImagen guardada:", png_path)

    if args.show:
        plt.show()

    plt.close(fig)

if __name__ == "__main__":
    main()