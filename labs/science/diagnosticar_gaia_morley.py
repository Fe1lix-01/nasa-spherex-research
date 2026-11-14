
import numpy as np
import astropy.units as u

from astropy.coordinates import SkyCoord
from astropy.time import Time
from astroquery.gaia import Gaia

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

Gaia.MAIN_GAIA_TABLE = "gaiadr3.gaia_source"
Gaia.ROW_LIMIT = 200


def numero(row, columna):
    try:
        valor = row[columna]

        if np.ma.is_masked(valor):
            return None

        valor = float(valor)

        if not np.isfinite(valor):
            return None

        return valor
    except (KeyError, TypeError, ValueError):
        return None


def propagar(ra, dec, pmra, pmdec, fecha):
    """
    Aproximacion de movimiento propio desde J2016.0.
    Sin paralaje, distancia ni velocidad radial.
    """
    dt = fecha.tdb.jyear - 2016.0
    cosdec = np.cos(np.deg2rad(dec))

    ra_nueva = (
        ra + pmra * dt / (3.6e6 * cosdec)
    ) % 360.0

    dec_nueva = dec + pmdec * dt / 3.6e6

    return SkyCoord(
        ra=ra_nueva * u.deg,
        dec=dec_nueva * u.deg,
        frame="icrs",
    )


for nombre, datos in FUENTES.items():

    print("\n" + "=" * 55)
    print("DIAGNOSTICO GAIA — FUENTE", nombre)
    print("=" * 55)

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

    de_obs, dn_obs = obs1.spherical_offsets_to(obs2)

    print(
        "Desplazamiento observado:",
        round(de_obs.arcsec, 4),
        round(dn_obs.arcsec, 4),
        "arcsec"
    )

    try:
        job = Gaia.cone_search_async(
            obs1,
            radius=30 * u.arcsec,
            columns=[
                "source_id",
                "ra",
                "dec",
                "pmra",
                "pmdec",
                "astrometric_params_solved",
            ],
        )

        tabla = job.get_results()

    except Exception as e:
        print("ERROR DE CONSULTA:", repr(e))
        continue

    print("\nFuentes Gaia encontradas:", len(tabla))

    candidatos = []
    con_pm = 0

    for fila in tabla:
        ra = numero(fila, "ra")
        dec = numero(fila, "dec")
        pmra = numero(fila, "pmra")
        pmdec = numero(fila, "pmdec")

        if ra is None or dec is None:
            continue

        source_id = str(fila["source_id"])

        if pmra is None or pmdec is None:
            # Gaia tiene posicion, pero no PM usable
            catalogo = SkyCoord(
                ra * u.deg,
                dec * u.deg,
                frame="icrs",
            )

            candidatos.append({
                "id": source_id,
                "tiene_pm": False,
                "separacion": obs1.separation(
                    catalogo
                ).arcsec,
            })
            continue

        con_pm += 1

        try:
            g1 = propagar(
                ra, dec, pmra, pmdec, T1
            )

            g2 = propagar(
                ra, dec, pmra, pmdec, T2
            )

            sep1 = obs1.separation(g1).arcsec
            sep2 = obs2.separation(g2).arcsec

            ge, gn = g1.spherical_offsets_to(g2)

            candidatos.append({
                "id": source_id,
                "tiene_pm": True,
                "separacion": sep1,
                "separacion_2026": sep2,
                "pmra": pmra,
                "pmdec": pmdec,
                "este": ge.arcsec,
                "norte": gn.arcsec,
            })

        except Exception as e:
            print(
                "Error procesando",
                source_id,
                repr(e)
            )

    print("Fuentes con movimiento propio:", con_pm)

    candidatos.sort(
        key=lambda c: c["separacion"]
    )

    print("\nCANDIDATOS MAS CERCANOS:")

    for c in candidatos[:5]:
        print("\nGaia ID:", c["id"])
        print(
            "Separacion 2025:",
            round(c["separacion"], 3),
            "arcsec"
        )

        if not c["tiene_pm"]:
            print(
                "Sin movimiento propio catalogado."
            )
            print(
                "Separacion calculada en J2016.0."
            )
            continue

        print(
            "Separacion 2026:",
            round(c["separacion_2026"], 3),
            "arcsec"
        )

        print(
            "Gaia PM RA/Dec:",
            c["pmra"],
            c["pmdec"],
            "mas/yr"
        )

        print(
            "Gaia esperado E/N:",
            round(c["este"], 4),
            round(c["norte"], 4),
            "arcsec"
        )

        print(
            "Residuo E/N:",
            round(de_obs.arcsec - c["este"], 4),
            round(dn_obs.arcsec - c["norte"], 4),
            "arcsec"
        )

    print(
        "\nIMPORTANTE: coincidencias preliminares, "
        "sin paralaje ni incertidumbres."
    )
