from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


router = APIRouter(prefix="/api/v1/science", tags=["Science"])
PROJECT_ROOT = Path(__file__).resolve().parents[4]
M101_PREVIEW = PROJECT_ROOT / "labs/science/outputs/11_m101_canal_63.png"


@router.get("/m101/channel-63/preview", response_class=FileResponse)
def m101_channel_preview():
    """Vista exploratoria generada por el experimento de Santi."""
    if not M101_PREVIEW.is_file():
        raise HTTPException(status_code=503, detail="Vista previa no disponible")
    return FileResponse(M101_PREVIEW, media_type="image/png")
