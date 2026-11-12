from pathlib import Path

from pydantic import ValidationError

from app.core.paths import PROJECT_ROOT
from app.schemas.remote_catalog import RemoteCatalogSnapshot


M101_METADATA_PATH = (
    PROJECT_ROOT / "data" / "m101" / "observations.json"
)

class RemoteCatalogError(ValueError):
    """El registro remoto no pudo leerse o validarse."""


def load_m101_snapshot(
    path: Path | None = None,
) -> RemoteCatalogSnapshot | None:
    """Lee y valida el registro local de metadatos de M101."""
    if path is None:
        path = M101_METADATA_PATH

    try:
        content = path.read_text(encoding="utf-8")

    except FileNotFoundError:
        return None

    except (OSError, UnicodeError) as error:
        raise RemoteCatalogError(
            "No fue posible leer el registro remoto de M101."
        ) from error

    try:
        return RemoteCatalogSnapshot.model_validate_json(content)

    except ValidationError as error:
        raise RemoteCatalogError(
            "El registro remoto de M101 tiene una estructura inválida."
        ) from error