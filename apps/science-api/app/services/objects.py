import re
from uuid import NAMESPACE_URL, uuid5

from app.services import observations as observations_service


# Reconoce el formato de los archivos del catálogo actual.
# Captura el nombre completo sin dividirlo por espacios.
OBJECT_FILENAME_PATTERN = re.compile(
    r"^(?P<name>.+)_D[1-6]_.+\.fits$"
)


def extract_object_name(filename: str) -> str:
    """Extrae el nombre del objeto según el formato del catálogo."""
    match = OBJECT_FILENAME_PATTERN.fullmatch(filename)

    if match is None:
        raise ValueError("Nombre de archivo no reconocido por el catálogo")

    name = match.group("name").strip()

    if not name:
        raise ValueError("El archivo no contiene un nombre de objeto")

    return name


def make_object_id(name: str) -> str:
    """Genera un identificador estable y utilizable en URLs."""
    return str(uuid5(NAMESPACE_URL, f"eter:astronomical-object:{name}"))


def list_objects(q: str | None = None) -> list[dict]:
    """Agrupa las observaciones existentes por nombre de objeto."""
    observations = observations_service.list_observations()
    grouped = {}

    for observation in observations:
        name = extract_object_name(observation["filename"])

        if name not in grouped:
            grouped[name] = {
                "id": make_object_id(name),
                "name": name,
                "observations": [],
            }

        grouped[name]["observations"].append(observation)

    objects = []

    for name in sorted(grouped, key=str.casefold):
        item = grouped[name]

        associated_observations = sorted(
            item["observations"],
            key=lambda observation: observation["id"],
        )

        objects.append(
            {
                "id": item["id"],
                "name": item["name"],
                "observation_count": len(associated_observations),
                "detectors": sorted(
                    {
                        observation["detector"]
                        for observation in associated_observations
                    }
                ),
                "observations": associated_observations,
            }
        )

    if q is not None:
        search = q.strip().casefold()
        objects = [
            item
            for item in objects
            if search in item["name"].casefold()
        ]

    return objects


def get_object(object_id: str) -> dict | None:
    """Busca un objeto por su identificador estable."""
    for item in list_objects():
        if item["id"] == object_id:
            return item

    return None