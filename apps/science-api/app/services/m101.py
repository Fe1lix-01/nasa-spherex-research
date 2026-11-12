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

        # Validar el número de canal antes de utilizarlo como índice.
    if isinstance(canal, bool) or not isinstance(canal, (int, np.integer)):
        raise ValueError("El canal debe ser un número entero.")

    if canal < 1:
        raise ValueError("El canal debe ser mayor o igual a 1.")

    indice = canal - 1

    with fits.open(archivo) as hdul:
        # Comprobar que existan las extensiones necesarias.
        requeridas = ("IMAGE", "NHITS", "FLAGS", "SPECTRAL_CHANNELS")
        faltantes = [nombre for nombre in requeridas if nombre not in hdul]

        if faltantes:
            raise ValueError(
                "El FITS carece de extensiones requeridas: "
                + ", ".join(faltantes)
            )

        cubo_imagen = hdul["IMAGE"].data
        cubo_hits = hdul["NHITS"].data
        cubo_flags = hdul["FLAGS"].data

        # Cada cubo debe tener tres dimensiones: canal, fila y columna.
        for nombre, datos in (
            ("IMAGE", cubo_imagen),
            ("NHITS", cubo_hits),
            ("FLAGS", cubo_flags),
        ):
            if datos is None:
                raise ValueError(f"La extensión {nombre} no contiene datos.")

            if datos.ndim != 3:
                raise ValueError(
                    f"La extensión {nombre} debe tener tres dimensiones "
                    "(canal, fila, columna)."
                )

            if any(dimension == 0 for dimension in datos.shape):
                raise ValueError(
                    f"La extensión {nombre} contiene dimensiones vacías."
                )

        # Los tres cubos deben describir los mismos canales y píxeles.
        if (
            cubo_imagen.shape != cubo_hits.shape
            or cubo_imagen.shape != cubo_flags.shape
        ):
            raise ValueError(
                "IMAGE, NHITS y FLAGS deben tener las mismas dimensiones."
            )

        # Evitar operaciones sobre textos, números complejos u otros tipos.
        if cubo_imagen.dtype.kind not in "iuf":
            raise ValueError("IMAGE debe contener valores numéricos reales.")

        if cubo_hits.dtype.kind not in "iuf":
            raise ValueError("NHITS debe contener valores numéricos reales.")

        # Las operaciones de bits requieren valores enteros.
        if cubo_flags.dtype.kind not in "iu":
            raise ValueError("FLAGS debe contener valores enteros.")

        numero_canales = cubo_imagen.shape[0]

        if canal > numero_canales:
            raise ValueError(
                f"El canal {canal} no existe. "
                f"El FITS contiene {numero_canales} canales."
            )

        # Validar la tabla de información espectral.
        channels = hdul["SPECTRAL_CHANNELS"].data

        if channels is None:
            raise ValueError("SPECTRAL_CHANNELS no contiene datos.")

        if channels.ndim != 1:
            raise ValueError(
                "SPECTRAL_CHANNELS debe ser una tabla de filas espectrales."
            )

        nombres_columnas = channels.dtype.names or ()

        if "WAVELENGTH" not in nombres_columnas:
            raise ValueError(
                "SPECTRAL_CHANNELS carece de la columna WAVELENGTH."
            )

        if indice >= len(channels):
            raise ValueError(
                f"SPECTRAL_CHANNELS no contiene información del canal {canal}."
            )

        valor_longitud = channels["WAVELENGTH"][indice]

        if np.ndim(valor_longitud) != 0:
            raise ValueError(
                "WAVELENGTH debe contener un único valor por canal."
            )

        try:
            longitud_onda = float(valor_longitud)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                "La longitud de onda del canal debe ser numérica."
            ) from error

        if not np.isfinite(longitud_onda) or longitud_onda <= 0:
            raise ValueError(
                "La longitud de onda del canal debe ser finita y positiva."
            )

        # Copiar los planos después de validar su estructura.
        imagen = cubo_imagen[indice].copy()
        hits = cubo_hits[indice].copy()
        flags = cubo_flags[indice].copy()

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