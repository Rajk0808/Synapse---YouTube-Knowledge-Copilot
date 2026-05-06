from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_notebook(mock_client_db):
    mock_response = MagicMock()
    mock_response.data = [{
        'notebook_id' : '12345678',
        'user_id' : "1",
        'title' : 'raj',
        'description' : ''
    }]

    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

    response = client.get('/notebooks/get/',params={
        'user_id'  : "1"
    })

    assert response.status_code == 200
    data = response.json()
    assert data[0]['notebook_id'] == '12345678'
    assert data[0]['title'] == 'raj'

def test_get_notebook_nonexist_user(mock_client_db):
    mock_response = MagicMock()
    mock_response.data = []  
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

    response = client.get('/notebooks/get/',params={
        'user_id'  : 1
    })
    assert response.status_code == 200
    data = response.json()
    assert data == []


def test_add_notebook(mock_client_db):
    mock_client_db.table.return_value.insert.return_value.execute.return_value = MagicMock()

    payload = {'user_id': '1', 'title': 'raj', 'description': ''}
    response = client.post('/notebook/add/', json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data['message'] == 'Notebook created'
    assert data['title'] == 'raj'


def test_notebook_rename(mock_client_db):
    mock_response = MagicMock()
    mock_response.data = None
    mock_client_db.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_response

    response = client.post(
        '/notebook/rename/',
        json = {
            'new_title' : 'raj',
            'notebook_id'  : '123'
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data['message'] == 'NoteBook Renamed.'
    assert data['title'] == 'raj'


def test_notebook_delete(mock_client_db):
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.side_effect = [
        MagicMock(data=[{'conversation_id': '123456'}, {'conversation_id': '1234567'}]),
        MagicMock(data=[{'source_id': '123456'}, {'source_id': '1234567'}]),
    ]
    mock_client_db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    response = client.post(          
        '/notebook/delete/',
        json={'notebook_id': '1234', 'title': 'raj'}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['message'] == 'NoteBook Deleted.'   # ← match main.py casing exactly
    assert data['title'] == 'raj'