from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

#============================================
# /notebook/sources/add/
#============================================
def test_add_source_valid_input(mock_ingest, mock_client_db):
    insert_table = MagicMock()
    insert_table.insert.return_value.execute.return_value = MagicMock(data=[{'source_id' : '12345'}])

    select_table = MagicMock()
    select_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{'source_id': '12345'}]
    )

    update_table = MagicMock()
    update_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    mock_client_db.table.side_effect = [
        insert_table,   # table('Source') → insert
        select_table,   # table('Source') → select source_id
        update_table,   # table('Source') → update filename
    ]

    mock_ingest.invoke.return_value = {'document': {'title': 'raj'}}

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
def test_add_source_valid_input_with_error(mock_ingest, mock_client_db):
    insert_table = MagicMock()
    insert_table.insert.return_value.execute.return_value = MagicMock(data=[{'source_id': '12345'}])

    select_table = MagicMock()
    select_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{'source_id': '12345'}]
    )

    update_table = MagicMock()
    update_table.update.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    mock_client_db.table.side_effect = [
        insert_table,   # table('Source') → insert
        select_table,   # table('Source') → select source_id
        update_table,   # table('Source') → update filename
    ]

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
def test_delete_notebook_with_conversations_and_sources(mock_client_db):
    # 1 — Conversation select
    conv_select = MagicMock()
    conv_select.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{'conversation_id': 'c1'}, {'conversation_id': 'c2'}]
    )

    # 2 — Message delete conv 1
    msg_delete_1 = MagicMock()
    msg_delete_1.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    # 3 — Message delete conv 2
    msg_delete_2 = MagicMock()
    msg_delete_2.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    # 4 — Conversation delete
    conv_delete = MagicMock()
    conv_delete.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    # 5 — Source select
    source_select = MagicMock()
    source_select.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{'source_id': 's1'}, {'source_id': 's2'}]
    )

    # 6 — SourceChunk delete source 1
    chunk_delete_1 = MagicMock()
    chunk_delete_1.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    # 7 — SourceChunk delete source 2
    chunk_delete_2 = MagicMock()
    chunk_delete_2.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    # 8 — Source delete
    source_delete = MagicMock()
    source_delete.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    # 9 — Notebook delete
    notebook_delete = MagicMock()
    notebook_delete.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    mock_client_db.table.side_effect = [
        conv_select,    # 1
        msg_delete_1,   # 2
        msg_delete_2,   # 3
        conv_delete,    # 4
        source_select,  # 5
        chunk_delete_1, # 6
        chunk_delete_2, # 7
        source_delete,  # 8
        notebook_delete # 9
    ]

    response = client.post('/notebook/delete/', json={
        'notebook_id': 'nb1',
        'title': 'raj'
    })

    assert response.status_code == 200
    data = response.json()
    assert data['message'] == 'NoteBook Deleted.'
    assert data['title'] == 'raj'


def test_delete_notebook_no_conversations_no_sources(mock_client_db):
    # 1 — Conversation select  empty
    conv_select = MagicMock()
    conv_select.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    # 2 — Source select empty
    source_select = MagicMock()
    source_select.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    # 3 — Notebook delete
    notebook_delete = MagicMock()
    notebook_delete.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=None)

    mock_client_db.table.side_effect = [
        conv_select,    # 1 — no conversations, skips messages + conv delete
        source_select,  # 2 — no sources, skips chunk + source delete
        notebook_delete # 3
    ]

    response = client.post('/notebook/delete/', json={
        'notebook_id': 'nb1',
        'title': 'raj'
    })
    

    assert response.status_code == 200
    data = response.json()
    assert data['message'] == 'NoteBook Deleted.'

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
    mock_sources = MagicMock()
    mock_sources.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{'source_id' : '12345'}])

    mock_client_db.table.side_effect = [
        mock_sources
    ]
    response = client.get('/notebook/sources/',
                          params = {'notebook_id' : ''}
                          ) 
    assert response.status_code == 200
    data = response.json()
    assert data['sources'] == [{'source_id': '12345'}]

def test_if_source_not_exist(mock_client_db):
    mock_sources = MagicMock()
    mock_sources.table.select.return_value.eq.return_value.execute.return_value = None

    mock_client_db.table.side_effect =[
        mock_sources
    ]
    response = client.get('/notebook/sources/',
                          params = {'notebook_id' : ''}
                          ) 
    assert response.status_code == 200
    data = response.json()
    assert data['sources'] == {}
