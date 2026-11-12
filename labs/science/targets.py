"""Catálogo de objetos candidatos del proyecto.

Aquí NO se escriben coordenadas a mano: solo el nombre con el que SIMBAD conoce al objeto.
El script de la canalización (10_candidatos.py) le pregunta a SIMBAD las coordenadas, el
movimiento propio y el paralaje, que es como se hace en astronomía profesional y evita
errores de dedo.

Los valores de respaldo (`respaldo`) solo se usan si SIMBAD no responde o no tiene el dato.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Target:
    """Un objeto candidato del visor."""

    key: str  # identificador corto, también es el nombre de la carpeta de imágenes
    alias: tuple[str, ...]  # nombres a probar en SIMBAD, en orden
    name: str  # nombre para mostrar en la interfaz
    kind: str  # tipo según el contrato del frontend
    summary: str  # explicación breve para la persona que usa el visor
    detector: str = "D2"  # detector de SPHEREx a consultar (D1 a D6)
    cutout_deg: float = 0.08  # ancho del recorte, en grados
    # Respaldo: ra y dec en grados (J2000), movimiento propio en mas/año, paralaje en mas.
    respaldo: dict = field(default_factory=dict)


TARGETS: dict[str, Target] = {
    "barnard": Target(
        key="barnard",
        alias=("GJ 699", "Barnard's star", "V2500 Oph"),
        name="Estrella de Barnard",
        kind="star",
        summary=(
            "Enana roja a unos 6 años luz, la estrella con el movimiento propio más rápido del "
            "cielo: se desplaza unos 10.3 segundos de arco por año. Las imágenes son recortes "
            "reales de SPHEREx obtenidos de IRSA, y la posición de cada época se calcula con su "
            "movimiento propio catalogado."
        ),
        respaldo={"ra": 269.452077, "dec": 4.693364, "pmra": -801.551, "pmdec": 10362.394, "plx": 546.9759},
    ),
    "wise0855": Target(
        key="wise0855",
        alias=("WISEA J085510.74-071442.5", "WISE J085510.83-071442.5", "WISE 0855-0714"),
        name="WISE 0855−0714",
        kind="brown_dwarf",
        summary=(
            "Enana marrón extremadamente fría (unos -23 °C), el objeto más frío conocido fuera "
            "del Sistema Solar, a 7.2 años luz. Casi no emite luz visible: brilla en infrarrojo, "
            "que es justo lo que mide SPHEREx. Su movimiento propio es enorme, unos 8.1 segundos "
            "de arco por año, así que se desplaza bastante entre épocas. Las imágenes son recortes "
            "reales de SPHEREx (4.4 a 5 micras), pero el objeto es tan débil que en una sola toma "
            "no se distingue del ruido: el marcador muestra su posición calculada con su movimiento "
            "propio catalogado, y al apilar las épocas solo aparece un indicio débil, no concluyente."
        ),
        detector="D6",
        respaldo={"ra": 133.795132, "dec": -7.245146, "pmra": -8123.7, "pmdec": 673.2, "plx": 439.0},
    ),
    "eps-indi-b": Target(
        key="eps-indi-b",
        alias=("eps Ind B", "* eps Ind B", "GJ 845 B", "eps Ind Ba"),
        name="Epsilon Indi B",
        kind="brown_dwarf",
        summary=(
            "Par de enanas marrones (Ba y Bb) que orbitan a la estrella Epsilon Indi A, a unos 12 "
            "años luz. Se desplazan por el cielo junto con su estrella, unos 4.7 segundos de arco "
            "por año, y además giran una alrededor de la otra."
        ),
        # Recorte más ancho: el par B está a unos 6.7 minutos de arco de la estrella principal,
        # así que con 0.25° caben los dos y se ve el sistema completo.
        cutout_deg=0.25,
        # Movimiento propio y paralaje del par Ba/Bb (Wikipedia / Gaia). La posición se resuelve
        # por nombre: NO se pone a mano porque está a varios minutos de arco de Epsilon Indi A
        # y una coordenada equivocada apuntaría a la estrella, no a las enanas marrones.
        respaldo={"pmra": 3981.977, "pmdec": -2466.832, "plx": 270.658},
    ),
    "rw-aur": Target(
        key="rw-aur",
        alias=("RW Aur", "V* RW Aur", "HD 240764"),
        name="RW Aurigae",
        kind="star",
        summary=(
            "Estrella joven y variable del tipo T Tauri, todavía rodeada por un disco de material. "
            "No cambia de posición de forma apreciable: lo que cambia es su brillo, a veces de "
            "forma brusca cuando el disco la oscurece. Sirve para distinguir un objeto que cambia "
            "de luz de uno que cambia de lugar."
        ),
        respaldo={"ra": 76.9560675, "dec": 30.40132611, "pmra": 2.641, "pmdec": -27.398, "plx": 6.4062},
    ),
    "kapteyn": Target(
        key="kapteyn",
        alias=("Kapteyn's star", "GJ 191", "HD 33793", "CD-44 1773"),
        name="Estrella de Kapteyn",
        kind="star",
        summary=(
            "Subenana roja a unos 13 años luz, una de las estrellas con mayor movimiento propio "
            "del cielo: se desplaza unos 8.7 segundos de arco por año. Pertenece al halo de la "
            "galaxia, es muy antigua y viaja a gran velocidad. Brilla bien en el infrarrojo "
            "cercano, que es lo que mide SPHEREx. Las imágenes son recortes reales de SPHEREx "
            "(IRSA) y la posición de cada época se calcula con su movimiento propio catalogado. "
            "Es tan brillante que el centro satura el detector, así que el núcleo se muestra en "
            "blanco: es un límite de la medición, no un hueco real."
        ),
        # Solo movimiento propio y paralaje (aprox., Hipparcos/Gaia). La posición NO se escribe a
        # mano: se resuelve por nombre en SIMBAD/Sesame para evitar apuntar a otro lugar.
        respaldo={"pmra": 6505.1, "pmdec": -5731.0, "plx": 254.2},
    ),
    "r-dra": Target(
        key="r-dra",
        alias=("R Dra", "V* R Dra"),
        name="R Draconis",
        kind="star",
        summary=(
            "Estrella variable de tipo Mira: una gigante roja que pulsa y cambia mucho de brillo a "
            "lo largo de unos 245 días. Como RW Aurigae, aquí lo que se observa entre épocas es el "
            "cambio de luz, no de posición. Es tan brillante que el centro satura el detector de "
            "SPHEREx, así que el núcleo se muestra en blanco: es un límite de la medición, no un "
            "hueco real."
        ),
        # Sin respaldo: la posición se resuelve por nombre. Su movimiento propio es pequeño, así
        # que si no se consigue, el script avanza con movimiento cero y lo avisa.
    ),
}
