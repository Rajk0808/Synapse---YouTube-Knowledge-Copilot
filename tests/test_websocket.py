from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_ws_existing_conversation(mock_client_db, mock_retrieve):
    conv_table = MagicMock()
    conv_table.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{'conversation_id': '123'}]  # conversation exists
    )

    messages_table = MagicMock()
    messages_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]  # no previous messages
    )

    insert_human_table = MagicMock()
    insert_human_table.insert.return_value.execute.return_value = MagicMock(data=None)

    insert_ai_table = MagicMock()
    insert_ai_table.insert.return_value.execute.return_value = MagicMock(data=None)

    mock_client_db.table.side_effect = [
        conv_table,          # Conversation select
        messages_table,      # Message last 6
        insert_human_table,  # Message insert human
        insert_ai_table,     # Message insert AI
    ]

    mock_retrieve.invoke.return_value = {'response': 'This is the AI answer'}

    with client.websocket_connect('/ws/chat?notebook_id=123') as ws:
        ws.send_text("What is this video about?")
        response = ws.receive_text()

    assert response == 'This is the AI answer'

def test_ws_new_conversation(mock_client_db, mock_retrieve):
    mock_client_db.table.side_effect = [
        MagicMock(data=[]),           # Conversation select → empty, no conv
        MagicMock(),                  # Conversation insert
        MagicMock(data=[{'conversation_id': '999'}]),  # Conversation select id
        MagicMock(data=[]),           # Message last 6
        MagicMock(),                  # Message insert human
        MagicMock(),                  # Message insert AI
    ]
    mock_retrieve.invoke.return_value = {'response': 'Hello!'}

    with client.websocket_connect('/ws/chat?notebook_id=new-nb') as ws:
        ws.send_text("hello")
        response = ws.receive_text()

    assert response == 'Hello!'

def test_ws_no_notebook_id(mock_client_db, mock_retrieve):
    mock_client_db.table.side_effect = [
        MagicMock(data=[{'conversation_id': '123'}]),
        MagicMock(data=[]),
        MagicMock(),
    ]

    with client.websocket_connect('/ws/chat?notebook_id=null') as ws:
        ws.send_text("hello")
        response = ws.receive_text()

    assert response == "Error: No notebook active. Please select a notebook to chat."

def test_ws_rag_error(mock_client_db, mock_retrieve):
    mock_client_db.table.side_effect = [
        MagicMock(data=[{'conversation_id': '123'}]),
        MagicMock(data=[]),
        MagicMock(),
    ]
    mock_retrieve.invoke.side_effect = Exception("RAG pipeline failed")

    with client.websocket_connect('/ws/chat?notebook_id=123') as ws:
        ws.send_text("hello")
        response = ws.receive_text()

    assert "An error occurred" in response