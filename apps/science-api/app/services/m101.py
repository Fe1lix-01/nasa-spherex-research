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
    """
    Genera una figura científica de M101 con tres paneles:
    imagen del canal, cobertura NHITS y máscara de calidad.

    El archivo FITS debe contener las extensiones:
    - IMAGE: cubo de imágenes espectrales.
    - NHITS: cantidad de observaciones por píxel.
    - FLAGS: banderas de calidad por píxel.
    - SPECTRAL_CHANNELS: metadatos de los canales espectrales.
    """

    # Validamos el número de canal antes de acceder al FITS.
    if not isinstance(canal, int) or isinstance(canal, bool) or canal < 1:
        raise ValueError("El canal debe ser un entero mayor o igual a 1.")

    indice = canal - 1

    # Abrimos el FITS y comprobamos que contenga las extensiones necesarias.
    with fits.open(archivo) as hdul:
        extensiones_requeridas = (
            "IMAGE",
            "NHITS",
            "FLAGS",
            "SPECTRAL_CHANNELS",
        )

        for extension in extensiones_requeridas:
            if extension not in hdul:
                raise ValueError(
                    f"El FITS no contiene la extensión requerida: {extension}."
                )

        # Recuperamos los datos de cada extensión.
        datos_imagen = hdul["IMAGE"].data
        datos_hits = hdul["NHITS"].data
        datos_flags = hdul["FLAGS"].data
        datos_canales = hdul["SPECTRAL_CHANNELS"].data

        # Comprobamos que las extensiones contengan datos.
        if any(
            datos is None
            for datos in (
                datos_imagen,
                datos_hits,
                datos_flags,
                datos_canales,
            )
        ):
            raise ValueError("Una o más extensiones FITS no contienen datos.")

        # Convertimos los datos a arreglos NumPy para validar sus dimensiones.
        datos_imagen = np.asarray(datos_imagen)
        datos_hits = np.asarray(datos_hits)
        datos_flags = np.asarray(datos_flags)

        # IMAGE, NHITS y FLAGS deben ser cubos tridimensionales.
        if datos_imagen.ndim != 3:
            raise ValueError("La extensión IMAGE debe tener tres dimensiones.")

        if datos_hits.ndim != 3:
            raise ValueError("La extensión NHITS debe tener tres dimensiones.")

        if datos_flags.ndim != 3:
            raise ValueError("La extensión FLAGS debe tener tres dimensiones.")

        # Los tres cubos deben tener exactamente la misma estructura.
        if (
            datos_imagen.shape != datos_hits.shape
            or datos_imagen.shape != datos_flags.shape
        ):
            raise ValueError(
                "Las extensiones IMAGE, NHITS y FLAGS tienen dimensiones incompatibles."
            )

        # Comprobamos que el canal solicitado exista en el cubo.
        numero_canales = datos_imagen.shape[0]

        if canal > numero_canales:
            raise ValueError(
                f"El FITS contiene solamente {numero_canales} canales."
            )

        # La extensión de metadatos debe contener un registro por canal.
        if len(datos_canales) < numero_canales:
            raise ValueError(
                "SPECTRAL_CHANNELS no contiene metadatos para todos los canales."
            )

        # Comprobamos que exista el campo de longitud de onda.
        nombres_campos = datos_canales.dtype.names or ()

        if "WAVELENGTH" not in nombres_campos:
            raise ValueError(
                "SPECTRAL_CHANNELS no contiene el campo WAVELENGTH."
            )

        # Copiamos los planos para utilizarlos después de cerrar el FITS.
        imagen = datos_imagen[indice].copy()
        hits = datos_hits[indice].copy()
        flags = datos_flags[indice].copy()

        # Recuperamos la longitud de onda correspondiente al canal.
        longitud_onda = float(datos_canales["WAVELENGTH"][indice])

    # Validamos que la longitud de onda sea un valor físico utilizable.
    if not np.isfinite(longitud_onda) or longitud_onda <= 0:
        raise ValueError(
            "La longitud de onda del canal debe ser un valor finito y positivo."
        )

    # Las banderas deben ser enteros para poder aplicar operaciones de bits.
    if not np.issubdtype(flags.dtype, np.integer):
        raise ValueError("La extensión FLAGS debe contener valores enteros.")

    # Conservamos las banderas de calidad utilizadas en el análisis original.
    # Bit 1: overflow.
    overflow = (flags & (1 << 1)) != 0

    # Bit 19: outlier.
    outlier = (flags & (1 << 19)) != 0

    # Un píxel es válido si tiene señal finita, cobertura positiva
    # y no presenta ninguna de las dos banderas excluidas.
    validos = (
        np.isfinite(imagen)
        & np.isfinite(hits)
        & (hits > 0)
        & ~overflow
        & ~outlier
    )

    # Evitamos generar una figura sin información científica válida.
    if not np.any(validos):
        raise ValueError(
            "No hay píxeles válidos para visualizar este canal."
        )

    # Sustituimos los píxeles inválidos por NaN para excluirlos
    # del cálculo de percentiles y de la visualización científica.
    imagen_limpia = np.where(validos, imagen, np.nan)

    # Calculamos límites robustos para evitar que valores extremos
    # dominen el contraste de la imagen.
    vmin, vmax = np.nanpercentile(imagen_limpia, [5, 99.5])

    # Matplotlib necesita límites distintos para representar correctamente
    # una imagen cuyos píxeles válidos tengan todos el mismo valor.
    if vmin == vmax:
        margen = max(abs(float(vmin)) * 1e-6, 1e-12)
        vmin -= margen
        vmax += margen

    # Creamos una figura sin depender de una interfaz gráfica.
    # FigureCanvasAgg permite generar imágenes PNG desde el backend.
    fig = Figure(figsize=(14, 4))
    FigureCanvasAgg(fig)

    # Distribuimos los tres paneles horizontalmente.
    axes = fig.subplots(1, 3)

    try:
        # Panel 1: intensidad científica del canal seleccionado.
        imagen_panel = axes[0].imshow(
            imagen_limpia,
            origin="lower",
            cmap="inferno",
            vmin=vmin,
            vmax=vmax,
        )

        axes[0].set_title(f"M101 - Canal {canal}")

        # Agregamos la escala de intensidad de la imagen.
        fig.colorbar(
            imagen_panel,
            ax=axes[0],
            label="MJy/sr",
            fraction=0.046,
        )

        # Panel 2: cobertura de observaciones por píxel.
        # Los píxeles sin cobertura se mantienen visibles para inspección.
        axes[1].imshow(
            hits,
            origin="lower",
            cmap="viridis",
        )

        axes[1].set_title("Cobertura NHITS")

        # Panel 3: máscara binaria de calidad.
        # Blanco representa píxeles válidos y negro los excluidos.
        axes[2].imshow(
            validos,
            origin="lower",
            cmap="gray",
            vmin=0,
            vmax=1,
        )

        axes[2].set_title("Máscara de calidad")

        # Aplicamos etiquetas espaciales consistentes a los tres paneles.
        for ax in axes:
            ax.set_xlabel("X [píxeles]")
            ax.set_ylabel("Y [píxeles]")

        # Indicamos el objeto y la longitud de onda visualizada.
        fig.suptitle(
            f"SPHEREx M101 - {longitud_onda:.3f} um"
        )

        # Ajustamos el espacio para evitar que los títulos y etiquetas
        # se encimen antes de guardar la figura.
        fig.tight_layout()

        # Creamos el directorio de salida si todavía no existe.
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)

        # Guardamos la figura como PNG.
        fig.savefig(ruta_salida, dpi=180)

    finally:
        # Liberamos los recursos de la figura incluso si ocurre un error.
        fig.clear()
