import pytest
from astropy.table import Table
from pydantic import ValidationError

from app.clients.irsa import IrsaResponseError
from app.schemas.sia import SiaQuery
from app.services.sia import transform_sia_results


def crear_tabla(collection):
    """Datos sintéticos para probar la transformación, sin consultar IRSA."""
    return Table(
        rows=[
            (
                "exposure-example",
                f"ivo://example/{collection}/exposure-example/D4",
                collection,
                "SPHEREx-D4",
                210.8,
                54.3,
                60816.5,
                60816.501,
                "https://example.org/image.fits",
                "image/fits",
            ),
        ],
        names=[
            "obs_id",
            "obs_publisher_did",
            "obs_collection",
            "energy_bandpassname",
            "s_ra",
            "s_dec",
            "t_min",
            "t_max",
            "access_url",
            "access_format",
        ],
    )


@pytest.mark.parametrize("collection", ["spherex_qr2", "spherex_qr3"])
def test_transforma_la_coleccion_solicitada(collection):
    query = SiaQuery(
        collection=collection,
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
        limit=2,
    )

    response = transform_sia_results(crear_tabla(collection), query)

    assert response.collection == collection
    assert response.query.collection == collection
    assert response.count == 1
    assert response.observations[0].collection == collection
    assert response.observations[0].product_id == (
        f"ivo://example/{collection}/exposure-example/D4"
    )


def test_rechaza_coleccion_distinta_a_la_solicitada():
    query = SiaQuery(
        collection="spherex_qr2",
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
    )

    with pytest.raises(IrsaResponseError):
        transform_sia_results(crear_tabla("spherex_qr3"), query)


def test_exige_identificador_del_producto():
    table = crear_tabla("spherex_qr2")
    table.remove_column("obs_publisher_did")

    query = SiaQuery(
        collection="spherex_qr2",
        ra=210.8022671,
        dec=54.34895,
        band="SPHEREx-D4",
    )

    with pytest.raises(IrsaResponseError):
        transform_sia_results(table, query)


def test_rechaza_coleccion_no_admitida():
    with pytest.raises(ValidationError):
        SiaQuery(
            collection="coleccion-inexistente",
            ra=210.8022671,
            dec=54.34895,
        )


def test_conserva_qr3_como_valor_predeterminado():
    query = SiaQuery(ra=269.44627, dec=4.76820)

    assert query.collection == "spherex_qr3"