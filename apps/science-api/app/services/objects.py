# Permite buscar patrones dentro de los nombres de archivos.
import re

# uuid5 genera identificadores deterministas:
# el mismo nombre y namespace producen siempre el mismo ID.
from uuid import NAMESPACE_URL, uuid5

# Servicios que proporcionan los catálogos locales y remotos.
from app.services import observations as observations_service
from app.services import remote_catalog as remote_catalog_service


# Expresión regular para reconocer nombres de objetos en archivos FITS.
# Captura el nombre completo antes del identificador del detector.
OBJECT_FILENAME_PATTERN = re.compile(
    r"^(?P<name>.+)_D[1-6]_.+\.fits$"
)


def extract_object_name(filename: str) -> str:
    """Extrae el nombre del objeto según el formato del catálogo FITS."""

    # Comprueba que el nombre completo coincida con el patrón.
    match = OBJECT_FILENAME_PATTERN.fullmatch(filename)

    # Rechaza los archivos que no respetan la convención.
    if match is None:
        raise ValueError(
            "Nombre de archivo no reconocido por el catálogo"
        )

    # Recupera el nombre capturado y elimina espacios exteriores.
    name = match.group("name").strip()

    # Evita aceptar nombres vacíos.
    if not name:
        raise ValueError(
            "El archivo no contiene un nombre de objeto"
        )

    return name


def make_object_id(name: str) -> str:
    """Genera un identificador estable para un objeto astronómico."""

    # UUID5 produce el mismo identificador para el mismo nombre.
    return str(
        uuid5(
            NAMESPACE_URL,
            f"eter:astronomical-object:{name}",
        )
    )


def _serialize_model(model) -> dict:
    """Convierte un modelo Pydantic en un diccionario JSON-compatible."""

    # mode="json" convierte tipos especiales como HttpUrl y AwareDatetime.
    return model.model_dump(mode="json")


def list_objects(q: str | None = None) -> list[dict]:
    """
    Construye el catálogo unificado de objetos astronómicos.

    Combina observaciones FITS locales y observaciones SIA remotas
    registradas para M101.
    """

    # =========================================================
    # 1. OBTENER Y AGRUPAR OBSERVACIONES LOCALES
    # =========================================================

    # Reutiliza el servicio existente de observaciones.
    local_observations = observations_service.list_observations()

    # Diccionario temporal indexado por nombre normalizado.
    grouped = {}

    # Recorre las observaciones disponibles en el catálogo local.
    for observation in local_observations:

        # Extrae el nombre del objeto desde el archivo FITS.
        name = extract_object_name(observation["filename"])

        # Normaliza el nombre para evitar duplicados por capitalización.
        normalized_name = name.casefold()

        # Conserva el nombre canónico para M101.
        display_name = (
            "M101"
            if normalized_name == "m101"
            else name
        )

        # Crea el grupo cuando aparece por primera vez.
        if normalized_name not in grouped:
            grouped[normalized_name] = {
                "id": make_object_id(display_name),
                "name": display_name,
                "observations": [],
            }

        # Agrega la observación al grupo correspondiente.
        grouped[normalized_name]["observations"].append(
            observation
        )

    # =========================================================
    # 2. CONSTRUIR OBJETOS LOCALES
    # =========================================================

    objects = []

    # Ordena los nombres para producir resultados consistentes.
    for normalized_name in sorted(grouped):

        item = grouped[normalized_name]

        # Ordena las observaciones por su identificador.
        associated_observations = sorted(
            item["observations"],
            key=lambda observation: observation["id"],
        )

        local_count = len(associated_observations)

        # Construye el objeto con sus datos locales.
        objects.append(
            {
                "id": item["id"],
                "name": item["name"],

                # Conteos separados por procedencia.
                "local_observation_count": local_count,
                "remote_observation_count": 0,
                "observation_count": local_count,

                # Detectores únicos y ordenados.
                "detectors": sorted(
                    {
                        observation["detector"]
                        for observation in associated_observations
                    }
                ),

                # Observaciones FITS locales.
                "observations": associated_observations,

                # Información remota vacía inicialmente.
                "remote_observations": [],
                "remote_association": None,
                "remote_query": None,
            }
        )

    # =========================================================
    # 3. CARGAR EL REGISTRO REMOTO DE M101
    # =========================================================

    # El servicio devuelve un RemoteCatalogSnapshot o None.
    #
    # Si el archivo no existe, devuelve None.
    # Si el archivo es inválido, lanza RemoteCatalogError.
    #
    # No capturamos ese error: debe llegar al router para producir
    # una respuesta HTTP 503.
    remote_snapshot = (
        remote_catalog_service.load_m101_snapshot()
    )

    # =========================================================
    # 4. INTEGRAR LAS OBSERVACIONES REMOTAS DE M101
    # =========================================================

    # Solo se integra M101 si existe un registro remoto válido.
    if remote_snapshot is not None:

        # Recupera las observaciones validadas por el esquema SIA.
        remote_observations = (
            remote_snapshot.result.observations
        )

        # Un registro válido sin observaciones no crea un objeto.
        if remote_observations:

            # Busca si M101 ya existe en el catálogo local.
            m101 = next(
                (
                    item
                    for item in objects
                    if item["name"].casefold() == "m101"
                ),
                None,
            )

            # Si no existe localmente, crea el objeto remoto.
            if m101 is None:
                m101 = {
                    "id": make_object_id("M101"),
                    "name": "M101",
                    "local_observation_count": 0,
                    "remote_observation_count": 0,
                    "observation_count": 0,
                    "detectors": [],
                    "observations": [],
                    "remote_observations": [],
                    "remote_association": None,
                    "remote_query": None,
                }

                objects.append(m101)

            # Serializa las observaciones remotas para la respuesta JSON.
            serialized_remote_observations = [
                _serialize_model(observation)
                for observation in remote_observations
            ]

            # Calcula los conteos de ambas fuentes.
            local_count = len(m101["observations"])
            remote_count = len(serialized_remote_observations)

            # Actualiza M101 sin crear un segundo objeto.
            m101.update(
                {
                    "id": make_object_id("M101"),
                    "name": "M101",

                    # Conteos independientes.
                    "local_observation_count": local_count,
                    "remote_observation_count": remote_count,

                    # Total combinado de observaciones.
                    "observation_count": (
                        local_count + remote_count
                    ),

                    # Observaciones del catálogo remoto.
                    "remote_observations": (
                        serialized_remote_observations
                    ),

                    # Asociación espacial documentada.
                    "remote_association": _serialize_model(
                        remote_snapshot.association
                    ),

                    # Parámetros de la consulta SIA.
                    "remote_query": _serialize_model(
                        remote_snapshot.result.query
                    ),

                    # Información de la vista científica.
                    "science_preview": {
                        "title": "M101 — Canal 63",
                        "description": (
                            "Imagen del canal, cobertura "
                            "y máscara de calidad."
                        ),
                    },
                }
            )

    # =========================================================
    # 5. APLICAR FILTRO DE BÚSQUEDA
    # =========================================================

    if q is not None:

        # Normaliza el término de búsqueda.
        search = q.strip().casefold()

        # Permite coincidencias parciales sin distinguir mayúsculas.
        objects = [
            item
            for item in objects
            if search in item["name"].casefold()
        ]

    # =========================================================
    # 6. DEVOLVER CATÁLOGO UNIFICADO
    # =========================================================

    # Ordena los objetos alfabéticamente.
    return sorted(
        objects,
        key=lambda item: item["name"].casefold(),
    )


def get_object(object_id: str) -> dict | None:
    """Busca un objeto por su identificador estable."""

    # Reutiliza el catálogo unificado para recuperar
    # tanto observaciones locales como información remota.
    for item in list_objects():

        # Devuelve el objeto completo si coincide el identificador.
        if item["id"] == object_id:
            return item

    # Si no existe, devuelve None para que el router responda 404.
    return None
