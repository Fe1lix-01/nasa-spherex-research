
import numpy as np
import astropy.units as u

from astropy.coordinates import SkyCoord
from astropy.time import Time
from astroquery.gaia import Gaia

# Posiciones medidas en los FITS reales de SPHEREx.
FUENTES = {
    "A": {
        "ra1": 295.41529234,
        "dec1": -15.20268499,
        "ra2": 295.41537870,
        "dec2": -15.20266118,
    },
    "B": {
        "ra1": 295.40293840,
        "dec1": -15.20003066,
        "ra2": 295.40303446,
        "dec2": -15.20009492,
    },
}

T1 = Time("2025-09-17T09:50:38.562", scale="utc")
T2 = Time("2026-09-15T13:32:11.649", scale="utc")
GAIA_EPOCH = Time(2016.0, format="jyear")

Gaia.MAIN_GAIA_TABLE = "gaiadr3.gaia_source"
Gaia.ROW_LIMIT = 200


def posicion_gaia(fila, fecha):
    """Propagación por movimiento propio, sin paralaje."""

    coord = SkyCoord(
        ra=float(fila["ra"]) * u.deg,
        dec=float(fila["dec"]) * u.deg,
        pm_ra_cosdec=float(fila["pmra"]) * u.mas / u.yr,
        pm_dec=float(fila["pmdec"]) * u.mas / u.yr,
        obstime=GAIA_EPOCH,
        frame="icrs",
    )

    return coord.apply_space_motion(
        new_obstime=fecha
    )


def desplazamiento(pos1, pos2):
    este, norte = pos1.spherical_offsets_to(pos2)

    return (
        este.to_value(u.arcsec),
        norte.to_value(u.arcsec),
    )


for nombre, datos in FUENTES.items():

    obs1 = SkyCoord(
        datos["ra1"] * u.deg,
        datos["dec1"] * u.deg,
        frame="icrs",
    )

    obs2 = SkyCoord(
        datos["ra2"] * u.deg,
        datos["dec2"] * u.deg,
        frame="icrs",
    )

    print("\n" + "=" * 55)
    print("MORLEY + GAIA DR3 — FUENTE", nombre)
    print("=" * 55)

    d_e, d_n = desplazamiento(obs1, obs2)

    print("SPHEREx desplazamiento:")
    print(f"Este: {d_e:.4f} arcsec")
    print(f"Norte: {d_n:.4f} arcsec")

    print("\nConsultando Gaia DR3...")

    # Búsqueda amplia para permitir movimiento
    # desde la época de referencia de Gaia.
    try:
        consulta = Gaia.cone_search_async(
            obs1,
            radius=20 * u.arcsec,
        )

        tabla = consulta.get_results()

    except Exception as error:
        print("Error de consulta Gaia:", error)
        continue

    candidatos = []

    for fila in tabla:

        if (
            np.ma.is_masked(fila["pmra"])
            or np.ma.is_masked(fila["pmdec"])
        ):
            continue

        if not np.all(np.isfinite([
            float(fila["pmra"]),
            float(fila["pmdec"]),
        ])):
            continue

        try:
            g1 = posicion_gaia(fila, T1)
            g2 = posicion_gaia(fila, T2)

            sep1 = obs1.separation(g1).arcsec
            sep2 = obs2.separation(g2).arcsec

            # Ordenación exploratoria del emparejamiento.
            score = np.hypot(sep1, sep2)

            ge, gn = desplazamiento(g1, g2)

            candidatos.append({
                "source_id": int(fila["source_id"]),
                "sep1": float(sep1),
                "sep2": float(sep2),
                "score": float(score),
                "este": float(ge),
                "norte": float(gn),
                "pmra": float(fila["pmra"]),
                "pmdec": float(fila["pmdec"]),
            })

        except Exception:
            continue

    candidatos.sort(
        key=lambda x: x["score"]
    )

    if not candidatos:
        print("No se encontraron candidatos con movimiento propio.")
        continue

    print("\nCandidatos de identificación Gaia:")

    for c in candidatos[:3]:

        print("\nGaia DR3:", c["source_id"])

        print(
            f"Separación en 2025: {c['sep1']:.3f} arcsec"
        )

        print(
            f"Separación en 2026: {c['sep2']:.3f} arcsec"
        )

        print(
            f"Gaia esperado Este: {c['este']:.4f} arcsec"
        )

        print(
            f"Gaia esperado Norte: {c['norte']:.4f} arcsec"
        )

        print(
            f"Residuo Este: {d_e - c['este']:.4f} arcsec"
        )

        print(
            f"Residuo Norte: {d_n - c['norte']:.4f} arcsec"
        )

    print(
        "\nNOTA: identificación preliminar. "
        "Faltan paralaje, errores astrométricos "
        "y validación de la asociación."
    )
