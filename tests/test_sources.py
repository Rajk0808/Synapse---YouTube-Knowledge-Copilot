from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

#============================================
# /notebook/sources/add/
#============================================

# valid input
def test_add_source_valid_input(mock_ingest, mock_client_db):
    mock_client_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=None)
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{'source_id': '12345'}]
    )
    mock_ingest.invoke.return_value = {'document': {'title': 'raj'}}
    mock_client_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    response = client.post(
        '/notebook/sources/add/',
        json={
            'user_id': '123',
            'notebook_id': '1234567',
            'source_type': '12345678',
            'url': 'https://youtube.com',
            'title': ''
        }
    )

    assert response.status_code == 200
    assert response.json() == 'raj'

# Valid input with error.
def test_add_source_valid_input_with_error(mock_client_db,mock_ingest):
    mock_client_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=None)
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{'source_id': '12345'}]
    )
    mock_ingest.invoke.side_effect = ValueError("Invalid source URL")

    response = client.post(
        '/notebook/sources/add/',
        json={
            'user_id': '123',
            'notebook_id': '1234567',
            'source_type': '12345678',
            'url': 'https://youtube.com',
            'title': ''
        }
    )


    assert response.status_code == 400
    data = response.json()
    assert data['detail'] == 'Invalid source URL'

# Invalid Input 
def test_add_source_invalid_input(mock_client_db,mock_ingest):
    mock_client_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=None)
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{'source_id': '12345'}]
    )
    mock_ingest.invoke.side_effect = ValueError("Invalid source URL")

    response = client.post(
        '/notebook/sources/add/',
        json={
            'user_id': 123,
            'notebook_id': '1234567',
            'source_type': '12345678',
            'url': 'https://youtube.com',
            'title': ''
        }
    )


    assert response.status_code == 422


#============================================
# /notebook/sources/delete/
#============================================
def test_delete_source_with_chunks(mock_client_db, mock_remove):
    mock_client_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={'source_id': '12345'}   
    )
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{'chunk_id': 'abc'}, {'chunk_id': 'def'}]   # chunks exist
    )
    mock_client_db.table.return_value.delete.return_value.eq.return_value.execute.return_value = [
        MagicMock(data=None),
        MagicMock(data=None),
        MagicMock(data=None)
    ]
    mock_remove.return_value = None

    response = client.post('/notebook/sources/delete/',
                json={
                    'notebook_id' : '',
                    'source_id' : 'str'
                })
    assert response.status_code == 200
    data = response.json()
    assert data['message'] == 'Source Deleted'

def test_delete_source_with_non_existing_source(mock_client_db, mock_remove):
    mock_client_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = [
        MagicMock(data={'data' : '' }),
        MagicMock(data={'data' : []})
    ]
    mock_client_db.table.return_value.delete.return_value.eq.returnn_value.execute.return_value = [
        MagicMock(data=None),
        MagicMock(data=None),
        MagicMock(data=None)
    ]
    mock_remove.side_effect = ValueError('Error in sources')

    response = client.post('/notebook/sources/delete/',
                json={
                    'notebook_id' : '',
                    'source_id' : 'str'
                })
    assert response.status_code == 404


#============================================
# /notebook/sources/
#============================================
def test_if_source_exist(mock_client_db):
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'source_id' : '12345'}])
    response = client.get('/notebook/sources/',
                          params = {'notebook_id' : ''}
                          ) 
    assert response.status_code == 200
    data = response.json()
    assert data['sources'] == [{'source_id': '12345'}]

def test_if_source_not_exist(mock_client_db):
    mock_client_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=None)
    response = client.get('/notebook/sources/',
                          params = {'notebook_id' : ''}
                          ) 
    assert response.status_code == 200
    data = response.json()
    assert data['sources'] == []

