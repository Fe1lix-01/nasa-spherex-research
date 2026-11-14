from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get('/api/v1/health')         ## Realizamos una peticion GET al endpoint ##

    assert response.status_code == 200             ## Se verifica que se cumpla la condicion ##

    assert response.json() == {                    ## Obtenemos la respuesta json para compararla ##
        'status': 'ok',
        'service': 'ETER Backend'
    }