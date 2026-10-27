from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_observations():
    response = client.get('/api/v1/observations')                  ## Realizamos la peticion a fastapi ##

    assert response.status_code == 200                             ## Se responde de manera correcta a la peticion ## 

    data = response.json()

    assert data['total'] >= 6                                      ## Se encuentra el numero de archivos ##

    detectors = { 
        observation['detector']
        for observation in data['observations']
    }

    assert detectors == {                                           ## Encuentra los 6 detectores esperados ##
        'D1', 'D2', 'D3',
        'D4', 'D5', 'D6'
    }