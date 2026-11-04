
from spexpi.spherex_pipeline import (
    PipelineConfig,
    query_spherex_cutouts
)

ra = 24.2412498
dec = 9.5630705

config = PipelineConfig(
    cutout_size_arcsec=90,
    download_dir="labs/science/data/spexpi",
    max_workers=2,
    download_backend="http"
)

print("Consultando observaciones SPHEREx...")

results = query_spherex_cutouts(
    ra,
    dec,
    config
)

print("Observaciones encontradas:", len(results))
print("Columnas:", results.colnames)

if len(results) > 0:
    print(results[:5])
else:
    print("No se encontraron observaciones.")
