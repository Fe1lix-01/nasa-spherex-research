import numpy as np
from astropy.table import Table
from astropy.time import Time
from pydantic import ValidationError
from app.clients.sia import SiaClient

from app.clients.irsa import IrsaResponseError
from app.schemas.sia import SiaObservation, SiaQuery, SiaResponse


# Columnas necesarias para construir nuestra respuesta.
REQUIRED_COLUMNS = {
    "obs_id",
    "obs_collection",
    "obs_publisher_did",
    "energy_bandpassname",
    "s_ra",
    "s_dec",
    "t_min",
    "t_max",
    "access_url",
    "access_format",
}


def required_value(row, column: str):
    """Obtiene un valor obligatorio y rechaza datos ausentes."""
    value = row[column]

    if np.ma.is_masked(value):
        raise ValueError(f"Falta un valor obligatorio en {column}")

    return value


def transform_sia_results(
    table: Table,
    query: SiaQuery,
) -> SiaResponse:
    """Filtra y normaliza los resultados recibidos desde IRSA SIA."""

    if not REQUIRED_COLUMNS.issubset(table.colnames):
        raise IrsaResponseError()

    observations = []

    try:
        for row in table:
            band = str(
                required_value(row, "energy_bandpassname")
            ).strip()

            # Conservamos únicamente el detector solicitado.
            if band != query.band:
                continue

            start_mjd = float(required_value(row, "t_min"))
            end_mjd = float(required_value(row, "t_max"))

            observation = SiaObservation(
                product_id=str(
                    required_value(row, "obs_publisher_did")
                ).strip(),
                observation_id=str(
                    required_value(row, "obs_id")
                ).strip(),
                collection=str(
                    required_value(row, "obs_collection")
                ).strip(),
                band=band,
                image_center_ra_deg=float(
                    required_value(row, "s_ra")
                ),
                image_center_dec_deg=float(
                    required_value(row, "s_dec")
                ),
                start_mjd=start_mjd,
                end_mjd=end_mjd,
                start_utc=Time(
                    start_mjd,
                    format="mjd",
                    scale="utc",
                ).isot + "Z",
                access_url=str(
                    required_value(row, "access_url")
                ).strip(),
                access_format=str(
                    required_value(row, "access_format")
                ).strip(),
            )

            if observation.collection != query.collection:
                raise ValueError(
                    "La colección recibida no coincide con la solicitada"
                )

            observations.append(observation)

        # Ordenamos antes de aplicar el límite.
        observations.sort(
            key=lambda item: (
                item.start_mjd,
                item.observation_id,
            )
        )

        selected = observations[:query.limit]

        return SiaResponse(
            collection=query.collection,
            query=query,
            count=len(selected),
            observations=selected,
        )

    except (
        ValueError,
        TypeError,
        OverflowError,
        ValidationError,
    ) as error:
        raise IrsaResponseError() from error

def list_sia_observations(query: SiaQuery) -> SiaResponse:
    """Consulta IRSA SIA y devuelve sus datos normalizados."""
    client = SiaClient()
    table = client.fetch_observations(query)

    return transform_sia_results(table, query)