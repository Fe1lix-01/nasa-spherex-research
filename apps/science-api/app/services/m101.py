from pathlib import Path

import numpy as np
from astropy.io import fits
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


def generar_figura_m101(
    archivo: Path,
    ruta_salida: Path,
    canal: int = 63,
) -> None:
    """Genera la imagen del canal, la cobertura y la máscara de M101."""

    if canal < 1:
        raise ValueError("El canal debe ser mayor o igual a 1.")

    indice = canal - 1

    with fits.open(archivo) as hdul:
        numero_canales = hdul["IMAGE"].data.shape[0]

        if canal > numero_canales:
            raise ValueError(
                f"El FITS contiene solamente {numero_canales} canales."
            )

        # Copiamos los planos para usarlos después de cerrar el FITS.
        imagen = hdul["IMAGE"].data[indice].copy()
        hits = hdul["NHITS"].data[indice].copy()
        flags = hdul["FLAGS"].data[indice].copy()

        channels = hdul["SPECTRAL_CHANNELS"].data
        longitud_onda = float(channels["WAVELENGTH"][indice])

    # Conservamos las banderas utilizadas en el script de Santi.
    overflow = (flags & (1 << 1)) != 0
    outlier = (flags & (1 << 19)) != 0

    validos = (
        np.isfinite(imagen)
        & (hits > 0)
        & ~overflow
        & ~outlier
    )

    if not np.any(validos):
        raise ValueError("No hay píxeles válidos para visualizar este canal.")

    imagen_limpia = np.where(validos, imagen, np.nan)
    vmin, vmax = np.nanpercentile(imagen_limpia, [5, 99.5])

    # Creamos una figura que puede guardarse desde el servidor.
    fig = Figure(figsize=(14, 4))
    FigureCanvasAgg(fig)
    axes = fig.subplots(1, 3)

    try:
        # Primer panel. Imagen científica del canal.
        imagen_panel = axes[0].imshow(
            imagen_limpia,
            origin="lower",
            cmap="inferno",
            vmin=vmin,
            vmax=vmax,
        )
        axes[0].set_title(f"M101 - Canal {canal}")

        fig.colorbar(
            imagen_panel,
            ax=axes[0],
            label="MJy/sr",
            fraction=0.046,
        )

        # Segundo panel. Cobertura por píxel.
        axes[1].imshow(
            hits,
            origin="lower",
            cmap="viridis",
        )
        axes[1].set_title("Cobertura NHITS")

        # Tercer panel. Máscara de píxeles válidos.
        axes[2].imshow(
            validos,
            origin="lower",
            cmap="gray",
            vmin=0,
            vmax=1,
        )
        axes[2].set_title("Máscara de calidad")

        for ax in axes:
            ax.set_xlabel("X [píxeles]")
            ax.set_ylabel("Y [píxeles]")

        fig.suptitle(f"SPHEREx M101 - {longitud_onda:.3f} um")
        fig.tight_layout()

        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(ruta_salida, dpi=180)

    finally:
        fig.clear()