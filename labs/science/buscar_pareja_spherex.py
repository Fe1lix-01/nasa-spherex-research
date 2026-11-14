
import argparse
import csv
from pathlib import Path

import numpy as np
import requests
from astropy.io import fits
from astropy.wcs import WCS
import astropy.units as u

RA = 295.4097841
DEC = -15.2231692

CARPETA = Path("recortes_morley")
CARPETA.mkdir(exist_ok=True)


def leer_candidatos():
    with open("candidatos_d6.csv", encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))

    candidatos = []

    for fila in filas:
        try:
            url = fila["url"].strip()
            mjd = float(fila["mjd"])

            if "/6/" not in url:
                continue

            candidatos.append({
                "obs_id": fila["obs_id"],
                "mjd": mjd,
                "url": url,
            })
        except (KeyError, ValueError):
            continue

    return sorted(candidatos, key=lambda x: x["mjd"])


def muestra_uniforme(filas, cantidad):
    if len(filas) <= cantidad:
        return filas

    indices = np.linspace(
        0, len(filas) - 1, cantidad
    ).round().astype(int)

    return [filas[i] for i in np.unique(indices)]


def descargar_recorte(fila):
    nombre = fila["url"].split("/")[-1]
    archivo = CARPETA / nombre

    # Reutilizar recortes descargados
    if archivo.exists():
        return archivo

    url = (
        fila["url"]
        + f"?center={RA},{DEC}&size=0.06"
    )

    print("Descargando:", fila["obs_id"])

    respuesta = requests.get(url, timeout=180)
    respuesta.raise_for_status()

    temporal = archivo.with_suffix(".part")
    temporal.write_bytes(respuesta.content)

    if temporal.stat().st_size < 2048:
        temporal.unlink()
        raise ValueError("Respuesta FITS demasiado pequeña")

    temporal.replace(archivo)

    return archivo


def inspeccionar(fila):
    archivo = descargar_recorte(fila)

    with fits.open(archivo) as hdul:
        image = hdul["IMAGE"].data
        variance = hdul["VARIANCE"].data
        flags = hdul["FLAGS"].data
        header = hdul["IMAGE"].header

        # WCS espacial
        spatial_wcs = WCS(
            header, fobj=hdul
        ).celestial

        x, y = spatial_wcs.world_to_pixel_values(
            RA, DEC
            
           
        )
        
        x = float(np.asarray(x).item())
        y = float(np.asarray(y).item())

        alto, ancho = image.shape

        if not (
            np.isfinite(x)
            and np.isfinite(y)
            and 6 <= x < ancho - 6
            and 6 <= y < alto - 6
        ):
            raise ValueError("Fuente fuera de región útil")

        ix = int(round(x))
        iy = int(round(y))

        if not (
            np.isfinite(image[iy, ix])
            and np.isfinite(variance[iy, ix])
            and variance[iy, ix] > 0
        ):
            raise ValueError("Píxel o varianza inválidos")

        # WCS espectral alternativo
        spectral_wcs = WCS(
            header, fobj=hdul, key="W"
        )

        spectral_wcs.sip = None

        wavelength, bandwidth = (
            spectral_wcs.pixel_to_world(x, y)
        )

        wavelength = float(
            wavelength.to_value(u.um)
        )

        bandwidth = float(
            bandwidth.to_value(u.um)
        )

        if not (
            np.isfinite(wavelength)
            and np.isfinite(bandwidth)
            and bandwidth > 0
        ):
            raise ValueError("Calibración espectral inválida")

        return {
            "obs_id": fila["obs_id"],
            "mjd": fila["mjd"],
            "wavelength": wavelength,
            "bandwidth": bandwidth,
            "flags": int(flags[iy, ix]),
            "archivo": str(archivo),
        }


def guardar_csv(nombre, registros):
    if not registros:
        return

    with open(
        nombre, "w", newline="", encoding="utf-8"
    ) as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=list(registros[0].keys())
        )
        writer.writeheader()
        writer.writerows(registros)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--por-epoca", type=int, default=8
    )

    parser.add_argument(
        "--incluir-abril", action="store_true"
    )

    args = parser.parse_args()

    candidatos = leer_candidatos()

    # Campañas de observación
    grupo_2025 = [
        c for c in candidatos
        if 60900 < c["mjd"] < 61000
    ]

    grupo_2026 = [
        c for c in candidatos
        if 61290 < c["mjd"] < 61330
    ]

    grupo_abril = [
        c for c in candidatos
        if 61140 < c["mjd"] < 61185
    ]

    seleccion = (
        muestra_uniforme(
            grupo_2025, args.por_epoca
        )
        +
        muestra_uniforme(
            grupo_2026, args.por_epoca
        )
    )

    if args.incluir_abril:
        seleccion += muestra_uniforme(
            grupo_abril, args.por_epoca
        )

    print("Inventario total:", len(candidatos))
    print("Recortes a revisar:", len(seleccion))

    mediciones = []

    for i, fila in enumerate(seleccion, 1):
        print(
            f"\n[{i}/{len(seleccion)}] "
            f"{fila['obs_id']}"
        )

        try:
            resultado = inspeccionar(fila)
            mediciones.append(resultado)

            print(
                "Longitud:",
                round(resultado["wavelength"], 5),
                "um"
            )
            print(
                "Ancho:",
                round(resultado["bandwidth"], 5),
                "um"
            )

        except Exception as error:
         import traceback

    print("Error al analizar:", fila["obs_id"])
    traceback.print_exc()

    guardar_csv(
        "mediciones_espectrales.csv",
        mediciones
    )

    anteriores = [
        m for m in mediciones
        if m["mjd"] < 61000
    ]

    posteriores = [
        m for m in mediciones
        if m["mjd"] > 61140
    ]

    parejas = []

    for a in anteriores:
        for b in posteriores:

            dias = b["mjd"] - a["mjd"]

            if dias < 180:
                continue

            ancho_promedio = (
                a["bandwidth"] + b["bandwidth"]
            ) / 2

            desajuste = (
                abs(
                    a["wavelength"]
                    - b["wavelength"]
                ) / ancho_promedio
            )

            cambio_ancho = (
                abs(
                    a["bandwidth"]
                    - b["bandwidth"]
                ) / ancho_promedio
            )

            parejas.append({
                "observacion_2025": a["obs_id"],
                "observacion_2026": b["obs_id"],
                "dias": round(dias, 2),
                "lambda_2025": a["wavelength"],
                "lambda_2026": b["wavelength"],
                "desajuste": desajuste,
                "cambio_ancho": cambio_ancho,
                "archivo_2025": a["archivo"],
                "archivo_2026": b["archivo"],
            })

    parejas.sort(
        key=lambda p: (
            p["desajuste"],
            p["cambio_ancho"],
        )
    )

    guardar_csv(
        "parejas_ordenadas.csv",
        parejas
    )

    print("\n" + "=" * 55)
    print("MORLEY — MEJORES PAREJAS ESPECTRALES")
    print("=" * 55)

    for pareja in parejas[:5]:
        print(
            "\n",
            pareja["observacion_2025"],
            "/",
            pareja["observacion_2026"]
        )

        print(
            "Longitudes:",
            round(pareja["lambda_2025"], 5),
            round(pareja["lambda_2026"], 5),
            "um"
        )

        print(
            "Desajuste:",
            round(pareja["desajuste"], 4)
        )

        print(
            "Días:",
            round(pareja["dias"], 2)
        )

    prometedoras = [
        p for p in parejas
        if p["desajuste"] < 0.25
        and p["cambio_ancho"] < 0.25
    ]

    print(
        "\nParejas prometedoras:",
        len(prometedoras)
    )

    if not prometedoras:
        print(
            "Ampliar búsqueda. "
            "No ejecutar ZOGY todavía."
        )
    else:
        print(
            "Validar CWAVE, CBAND, PSF "
            "y calidad antes de ZOGY."
        )


if __name__ == "__main__":
    main()
