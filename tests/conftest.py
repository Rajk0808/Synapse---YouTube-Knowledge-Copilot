import os
import sys

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

with patch("database.connection.get_client", return_value=MagicMock()):
    import main

client = TestClient(main.app)

@pytest.fixture(autouse=True)
def mock_client_db():
    yield main.client_db

@pytest.fixture(autouse=True)
def mock_ingest():
    with patch("main.Ingest") as mock_ingest_class:
        mock_instance = MagicMock()
        mock_ingest_class.return_value = mock_instance  # Ingest() returns mock_instance
        yield mock_instance    

@pytest.fixture(autouse=True)
def mock_remove():
    with patch('main.Remove') as mock_remove_class:
        mock_instance = MagicMock()
        mock_remove_class.return_value = mock_instance
    yield mock_instance


@pytest.fixture
def mock_retrieve():
    with patch("main.retrieve") as mock_retrieve_class:  
        mock_instance = MagicMock()
        mock_retrieve_class.return_value = mock_instance
        yield mock_instance