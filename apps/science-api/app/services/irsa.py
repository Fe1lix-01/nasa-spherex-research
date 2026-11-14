import csv
import io

from astropy.time import Time
from pydantic import ValidationError

from app.clients.irsa import IrsaClient, IrsaResponseError
from app.schemas.irsa import (
    IrsaObservation,
    IrsaQuery,
    IrsaResponse,
)


REQUIRED_COLUMNS = {
    "time_bounds_lower",
    "time_bounds_upper",
    "energy_bandpassname",
    "cutout_url",
}


def normalize_observations(
    csv_text: str,
    query: IrsaQuery,
) -> IrsaResponse:
    """Convierte un CSV externo en la respuesta de nuestra API."""

    try:
        reader = csv.DictReader(
            io.StringIO(csv_text.lstrip("\ufeff")),
            strict=True,
        )

        columns = reader.fieldnames

        # También detecta HTML o XML devueltos con HTTP 200:
        # no tendrán las columnas esperadas.
        if columns is None:
            raise ValueError("Falta la cabecera")

        if not REQUIRED_COLUMNS.issubset(columns):
            raise ValueError("Faltan columnas requeridas")

        if len(columns) != len(set(columns)):
            raise ValueError("Hay columnas duplicadas")

        observations = []

        for row in reader:
            # Detecta filas con más o menos campos de lo esperado.
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Fila CSV incompleta o irregular")

            band = row["energy_bandpassname"].strip()

            if band != query.band:
                raise ValueError("Banda distinta a la solicitada")

            start_mjd = float(row["time_bounds_lower"])
            end_mjd = float(row["time_bounds_upper"])

            # Derivar la fecha del dato recibido antes de crear el modelo.
            start_utc = (
                Time(start_mjd, format="mjd", scale="utc").isot
                + "Z"
            )

            # Validar juntos todos los valores finales de la observación.
            observation = IrsaObservation(
                start_mjd=start_mjd,
                end_mjd=end_mjd,
                start_utc=start_utc,
                band=band,
                cutout_url=row["cutout_url"].strip(),
            )

            observations.append(observation)

        return IrsaResponse(
            query=query,
            count=len(observations),
            observations=observations,
        )

    except (
        csv.Error,
        ValueError,
        TypeError,
        OverflowError,
        ValidationError,
    ):
        # No mostramos filas ni mensajes internos al usuario.
        raise IrsaResponseError() from None


def search_observations(query: IrsaQuery) -> IrsaResponse:
    """Coordina la consulta externa y la transformación."""

    client = IrsaClient()
    csv_text = client.fetch_observations_csv(query)

    return normalize_observations(csv_text, query)