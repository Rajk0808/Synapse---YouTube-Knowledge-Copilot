from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_notebook(mock_client_db):
    mock_response = MagicMock()
    mock_response.data = None
    mock_client_db.table.return_value.select.return_Value.eq.return_value.execute.return_value = mock_response
    response = client.get(
        '/chat/',
        params = {'notebook_id' : '12345'}
    )

    assert response.status_code == 200


def test_get_prev_chats(mock_client_db):
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'conversation_id' : '123455'}])
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'conversation_id': '123455'}])

    response = client.get('/chat/get_prev_chat/',
                          params={'notebook_id' : '12345' })
    assert response.status_code == 200
    data = response.json()
    assert data['messages'] == [{'conversation_id': '123455'}]

def test_get_prev_chats_with_no_conv(mock_client_db):
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'conversation_id' : '123455'}])
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = None

    response = client.get('/chat/get_prev_chat/',
                          params={'notebook_id' : '12345' })
    assert response.status_code == 200
    data = response.json()
    assert data['messages'] == []