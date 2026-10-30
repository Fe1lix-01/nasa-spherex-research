# Permite buscar patrones dentro de los nombres de archivos.
import re
# uuid5 genera identificadores deterministas:
# con el mismo nombre y namespace obtenemos el mismo ID.
from uuid import NAMESPACE_URL, uuid5

# Importamos el módulo existente de observaciones.
# Lo llamamos observations_service para distinguirlo
# de las listas de observaciones que usamos después.
from app.services import observations as observations_service

# Expresión regular para reconocer los nombres del catálogo.
# Reconoce el formato de los archivos del catálogo actual.
# Captura el nombre completo sin dividirlo por espacios.
OBJECT_FILENAME_PATTERN = re.compile(
    r"^(?P<name>.+)_D[1-6]_.+\.fits$"
)


def extract_object_name(filename: str) -> str:
    """Extrae el nombre del objeto según el formato del catálogo."""
# Comprueba que el nombre completo coincida con el patrón.
    match = OBJECT_FILENAME_PATTERN.fullmatch(filename)
# Si no coincide, no podemos identificarlo con esta convención.
    if match is None:
        raise ValueError("Nombre de archivo no reconocido por el catálogo")

# Recupera la parte capturada como "name".
    # strip() elimina espacios al principio y al final.
    name = match.group("name").strip()

 # Evita aceptar un nombre vacío o formado solo por espacios.
    if not name:
        raise ValueError("El archivo no contiene un nombre de objeto")

    return name


def make_object_id(name: str) -> str:
    """Genera un identificador estable y utilizable en URLs."""
    # El prefijo identifica el uso del nombre dentro del proyecto.
    #
    # uuid5 no genera un ID aleatorio:
    # el mismo texto produce siempre el mismo UUID.
    #
    # str() lo convierte a texto para enviarlo en JSON
    # y utilizarlo dentro de una URL.

    return str(uuid5(NAMESPACE_URL, f"eter:astronomical-object:{name}"))


def list_objects(q: str | None = None) -> list[dict]:
    """Agrupa las observaciones existentes por nombre de objeto."""
    # q puede ser texto o None.
    # None significa que no se proporcionó una búsqueda.

    # Reutiliza el servicio de Marvin.
    # No abre nuevamente los FITS ni repite su lógica.
    observations = observations_service.list_observations()

    # Diccionario temporal:
    # cada clave será el nombre de un objeto.
    grouped = {}

# Recorremos cada observación del catálogo.
    for observation in observations:

         # Obtenemos el nombre del objeto desde el archivo.
        name = extract_object_name(observation["filename"])


# Si es la primera observación de ese objeto,
        # creamos su grupo.
        if name not in grouped:
            grouped[name] = {
                "id": make_object_id(name),
                "name": name,
                "observations": [],
            }

# Agregamos la observación a su grupo.
        #
        # Si después aparece otro archivo del mismo objeto,
        # se agrega aquí en lugar de crear otro objeto.
        grouped[name]["observations"].append(observation)

# Lista final de objetos.
    objects = []

# Ordenamos los nombres alfabéticamente.
    # casefold permite ordenar sin dar prioridad
    # a las diferencias de mayúsculas y minúsculas.
    for name in sorted(grouped, key=str.casefold):
        item = grouped[name]

# Ordenamos las observaciones por su identificador.
        # Esto hace que la salida tenga un orden consistente.
        associated_observations = sorted(
            item["observations"],
            key=lambda observation: observation["id"],
        )

# Construimos la información final del objeto.
        objects.append(
            {
                "id": item["id"],
                "name": item["name"],
                # Cuenta cuántos archivos tiene este objeto.
                "observation_count": len(associated_observations),
                 # El conjunto {...} elimina detectores repetidos.
                # sorted() los convierte en una lista ordenada.
                #
                # Dos archivos de D1 cuentan como dos
                # observaciones, pero D1 aparece una sola
                # vez en la lista de detectores.
                "detectors": sorted(
                    {
                        observation["detector"]
                        for observation in associated_observations
                    }
                ),
                 # Conservamos los datos de cada observación.
                "observations": associated_observations,
            }
        )

# ESTA ES LA PARTE QUE APLICA EL FILTRO POR NOMBRE.
    if q is not None:

        # Elimina espacios en los extremos de la búsqueda.
        # casefold() permite comparar sin distinguir
        # mayúsculas y minúsculas.
        search = q.strip().casefold()

        # Conserva solamente los objetos cuyo nombre
        # contiene el texto buscado.
        #
        # "in" permite coincidencias parciales:
        # "simp" está dentro de
        # "t2 simp j013656.5+093347.3".
        objects = [
            item
            for item in objects
            if search in item["name"].casefold()
        ]

# Sin coincidencias devuelve [].
    # Sin filtro devuelve todos los objetos.
    return objects


def get_object(object_id: str) -> dict | None:
    """Busca un objeto por su identificador estable."""
    # Reutiliza la agrupación anterior.
    for item in list_objects():
    # Si encontramos el ID, devolvemos el objeto completo.
        if item["id"] == object_id:
            return item

 # Si ningún objeto coincide, devolvemos None.
    # El router lo transformará en HTTP 404.
    return None