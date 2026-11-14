
from pathlib import Path
from astropy.io import fits

carpetas = [
    Path("SPHERExLVFSurveyData"),
    Path("SPHERExLVFSurveyData-1"),
]

for carpeta in carpetas:
    for archivo in carpeta.glob("*cutout.fits"):
        print("\n" + "=" * 60)
        print("ARCHIVO:", archivo.name)

        with fits.open(archivo) as hdul:
            hdul.info()

            for hdu in hdul:
                hdr = hdu.header
                print(f"\nEXTENSIÓN: {hdu.name}")

                for clave in [
                    "DATE-OBS", "MJD-OBS",
                    "MJD-BEG", "OBSID",
                    "CRVAL1", "CRVAL2",
                    "BUNIT", "NAXIS1", "NAXIS2",
                ]:
                    if clave in hdr:
                        print(clave, "=", hdr[clave])
