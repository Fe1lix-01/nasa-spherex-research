from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import requests
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.visualization import ImageNormalize, PercentileInterval, AsinhStretch
from astropy.wcs import WCS
import astropy.units as u


def main():
    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / "outputs" / "practica_7"
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = base_dir / "outputs" / "observaciones_irsa.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"No se encontró el CSV de la práctica 6:\n{csv_path}"
        )

    observations = Table.read(csv_path, format="ascii.csv")

    if len(observations) == 0:
        raise ValueError("El CSV no contiene observaciones.")

    observation = observations[0]

    url = str(observation["cutout_url"])
    ra = float(observation["query_ra_deg"])
    dec = float(observation["query_dec_deg"])

    print("Observación seleccionada:")
    print("Banda:", observation["energy_bandpassname"])
    print("Inicio UTC:", observation["start_utc"])
    print(f"Posición solicitada: RA={ra}, Dec={dec} grados")
    print("URL:", url)

    # 1. Descargar solamente el recorte de la primera fila.
    fits_path = output_dir / "cutout.fits"

    print("\nDescargando recorte...")

    response = requests.get(url, timeout=(15, 120))
    response.raise_for_status()
    fits_path.write_bytes(response.content)

    print("Archivo guardado:", fits_path)
    print(f"Tamaño: {fits_path.stat().st_size / 1024:.1f} KiB")

    # 2. Abrir el FITS e inspeccionar sus secciones.
    with fits.open(fits_path) as hdul:
        print("\nResumen de las HDU:")
        hdul.info()

        print("\nDetalles de cada HDU:")

        for index, hdu in enumerate(hdul):
            shape = None if hdu.data is None else hdu.data.shape
            dtype = None if hdu.data is None else hdu.data.dtype

            print(
                f"{index}: nombre={hdu.name}, "
                f"forma={shape}, tipo={dtype}"
            )

        print("\nNombres de las HDU:")
        print([hdu.name for hdu in hdul])

        if "IMAGE" not in hdul:
            raise ValueError(
                "Este FITS no tiene una extensión llamada IMAGE. "
                "Revisa el listado de HDU antes de continuar."
            )

        # 3. Leer la imagen científica.
        image_hdu = hdul["IMAGE"]
        image = np.asarray(image_hdu.data, dtype=float)
        header = image_hdu.header

        if image.ndim != 2:
            raise ValueError(
                f"Se esperaba una imagen 2D; se obtuvo {image.shape}."
            )

        print("\nMetadatos de IMAGE:")

        keywords = [
            "EXTNAME",
            "NAXIS",
            "NAXIS1",
            "NAXIS2",
            "BUNIT",
            "DETECTOR",
            "OBSID",
            "DATE-OBS",
            "MJD-OBS",
            "CTYPE1",
            "CTYPE2",
            "CUNIT1",
            "CUNIT2",
        ]

        for keyword in keywords:
            print(f"{keyword}: {header.get(keyword, 'No presente')}")

        # Guardar todas las cabeceras para revisarlas después.
        headers_path = output_dir / "cabeceras.txt"

        with headers_path.open("w", encoding="utf-8") as file:
            for index, hdu in enumerate(hdul):
                file.write(f"\nHDU {index}: {hdu.name}\n")
                file.write(hdu.header.tostring(sep="\n", padding=False))
                file.write("\n")

        # 4. Inspeccionar los valores numéricos.
        finite = image[np.isfinite(image)]

        if finite.size == 0:
            raise ValueError("La imagen no tiene valores finitos.")

        print("\nEstadísticas de IMAGE:")
        print("Dimensiones (filas, columnas):", image.shape)
        print("Píxeles totales:", image.size)
        print("Píxeles finitos:", finite.size)
        print("Mínimo:", float(np.min(finite)))
        print("Máximo:", float(np.max(finite)))
        print("Mediana:", float(np.median(finite)))

        # 5. Relacionar coordenadas del cielo con píxeles.
        spatial_wcs = WCS(header).celestial

        if not spatial_wcs.has_celestial:
            raise ValueError("No se encontró un WCS celeste utilizable.")

        target = SkyCoord(
            ra=ra * u.deg,
            dec=dec * u.deg,
            frame="icrs",
        )

        x, y = spatial_wcs.world_to_pixel(target)
        recovered = spatial_wcs.pixel_to_world(x, y)

        height, width = image.shape
        inside = (
            -0.5 <= x < width - 0.5
            and -0.5 <= y < height - 0.5
        )

        print("\nConversión con WCS:")
        print(f"Píxel de la posición solicitada: x={x:.3f}, y={y:.3f}")
        print("¿Está dentro del recorte?:", inside)
        print(f"RA recuperada: {recovered.icrs.ra.deg:.8f}")
        print(f"Dec recuperada: {recovered.icrs.dec.deg:.8f}")
        print(
            "Diferencia de ida y vuelta:",
            target.separation(recovered).arcsec,
            "segundos de arco",
        )

        # 6. Crear una vista previa.
        # El ajuste de contraste solo afecta al PNG.
        # No modifica el FITS.
        normalization = ImageNormalize(
            finite,
            interval=PercentileInterval(99),
            stretch=AsinhStretch(),
        )

        figure = plt.figure(figsize=(8, 6))
        axis = figure.add_subplot(111, projection=spatial_wcs)

        rendered = axis.imshow(
            image,
            origin="lower",
            cmap="gray",
            norm=normalization,
        )

        if inside:
            axis.plot(
                x,
                y,
                marker="+",
                color="red",
                markersize=12,
                linestyle="none",
                label="Posición consultada",
            )
            axis.legend()

        axis.set_xlabel("Ascensión recta")
        axis.set_ylabel("Declinación")
        axis.set_title("Recorte SPHEREx: vista previa")

        unit_label = header.get("BUNIT", "Unidad no indicada")
        figure.colorbar(
            rendered,
            ax=axis,
            label=f"Valor de IMAGE ({unit_label})",
        )

        png_path = output_dir / "cutout_preview.png"
        figure.savefig(png_path, dpi=150, bbox_inches="tight")
        plt.close(figure)

    print("\nPráctica terminada.")
    print("FITS:", fits_path)
    print("Cabeceras:", headers_path)
    print("Vista previa:", png_path)


if __name__ == "__main__":
    main()