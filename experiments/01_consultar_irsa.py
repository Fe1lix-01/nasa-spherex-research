
from spexpi.spherex_pipeline import (
    PipelineConfig,
    query_spherex_cutouts
)

# Objeto de ejemplo utilizado en SPExPI
RA = 24.2412498
DEC = 9.5630705

cfg = PipelineConfig(
    cutout_size_arcsec=90,
    download_dir="experiments/data",
    max_workers=2,
    download_backend="http"
)

print("Buscando observaciones SPHEREx...")

table = query_spherex_cutouts(RA, DEC, cfg)

print("Observaciones encontradas:", len(table))
print("Columnas:", table.colnames)

if len(table) > 0:
    print(table[:5])
else:
    print("No se encontraron observaciones.")

