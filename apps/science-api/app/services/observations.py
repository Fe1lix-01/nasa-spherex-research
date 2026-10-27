from pathlib import Path
import re

## Ubicacion principal del repo ##
PROJECT_ROOT = Path(__file__).resolve().parents[4]               

## Carpeta en donde se encuentran los fits ##
FITS_DIR = PROJECT_ROOT / "resources" / "objects" / "images" / "fits"

def list_observations():
    observations = []

    if not FITS_DIR.is_dir():
        raise FileNotFoundError(
            f'No existe en el directorio:{FITS_DIR}'
        )

    for file in sorted(FITS_DIR.glob('*.fits')):                  ## Busca los archivos .fits ##
        detector_match = re.search(r"_D([1-6])_", file.name)        ## Busca el identificador de cada archivo FITS [D1-D2-D3-D4-D5-D6] ##

        if detector_match is None:
            continue

        observations.append({                                    ## Metodo para agregar cada observacion a una lista ##
            'id': file.name,
            'detector': f'D{detector_match.group(1)}',
            'filename': file.name,
            'format': 'FITS'
        })

    return observations                                      ## Devolvemos la lista ##