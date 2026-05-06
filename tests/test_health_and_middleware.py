from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_returns_200():
    response = client.get('/health/')
    assert response.status_code == 200

def test_health_body():
    response = client.get('/health/')
    data = response.json()
    assert 'status' in data
    assert data['status'] == 'ok'

def test_send_put_or_delete():
    response = client.put('/health/')
    assert response.status_code == 405

    response = client.delete('/health/')
    assert response.status_code == 405

