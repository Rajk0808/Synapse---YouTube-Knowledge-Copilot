"""
pytest test suite for FastAPI YouTube Copilot
Covers: /transcript and /chat endpoints
Mocks: YouTube Transcript API, LangChain
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

#==============================================================
# FIXUTRES
#==============================================================

@pytest.fixture
def get_valid_youtube_url():
    return "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

@pytest.fixture
def get_invalid_youtube_url():
    return "https://www.notyoutube.com/watch?v=abc123"

@pytest.fixture
def mock_transcript():
    """Simulates a successful YouTube transcript response."""
    return [
        {"text": "Hello and welcome to this video.", "start": 0.0, "duration": 2.5},
        {"text": "Today we will talk about FastAPI.", "start": 2.5, "duration": 3.0},
        {"text": "It is a modern web framework for Python.", "start": 5.5, "duration": 3.5},
        {"text": "Let's get started with the basics.", "start": 9.0, "duration": 2.0},
    ]

@pytest.fixture
def mock_transcript_text():
    return (
        "Hello and welcome to this video. "
        "Today we will talk about FastAPI. "
        "It is a modern web framework for Python. "
        "Let's get started with the basics."
    )

@pytest.fixture
def mock_langchain_reponse():
    """Simulates a LangChain chain response."""
    mock = MagicMock()
    mock.invoke.return_value = {"output_text": "FastAPI is a modern Python web framework used to build APIs quickly."}
    return mock

class TimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            # Simulate a 35s timeout threshold
            return self.get_response(request)
        except Exception:
            # Catch timeout/long-running exception and return 504
            return MagicMock(status_code=504, content="Gateway Timeout")


#==============================================================
# HEALTH CHECKUP
#==============================================================
class HealthCheckUp:
    def test_health_returns_200(self):
        data = client.get('/heath')
        assert data.status_code == 200
    
    def test_health_body(self):
        response = client.get('/health')
        data = response.json()
        assert 'status' in data
        assert data['status'] == 'ok'


#==============================================================
# CHECK USER ENDPOINT
#==============================================================

class TestUserEndpoint:
    pass