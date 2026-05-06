from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_signup_success(mock_client_db):
    mock_client_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = None
    mock_insert_response = MagicMock()
    mock_insert_response.data = [{'user_id': 1}]
    mock_client_db.table.return_value.insert.return_value.execute.return_value = mock_insert_response

    response = client.post('/user/signup/', json={
        'username': 'testuser',
        'email': 'you@ex.com',
        'password': '12345678'
    })

    assert response.status_code == 200
    data = response.json()
    assert data['authenticated'] == True
    assert data['message'] == 'User created'

def test_signup_email_exists(mock_client_db):
    mock_response = MagicMock()
    mock_response.data = {'user_id': 1, 'email': 'existing@example.com'}
    mock_client_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

    response = client.post('/user/signup/', json={
        'username': 'testuser',
        'email': 'existing@example.com',
        'password': 'password123'
    })

    assert response.status_code == 200
    data = response.json()
    assert data['authenticated'] == False
    assert data['message'] == 'Email already exists'

def test_login_success(mock_client_db):
    mock_user = {
        'user_id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'password_hash': '$argon2id$v=19$m=65536,t=3,p=4$R9zW+l7QqzgAlpsXm5p9Og$NE7y7PtyH/I74mW9bleyfcPDrOBokhQjjEd2K5N5jCc'
    }
    mock_response = MagicMock()
    mock_response.data = mock_user
    mock_client_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

    with patch('argon2.PasswordHasher.verify', return_value=True):
        response = client.post('/user/login', json={
            'email': 'test@example.com',
            'password': '12345678'
        })

        assert response.status_code == 200
        data = response.json()
        assert data['user']['email'] == 'test@example.com'

def test_login_user_not_found(mock_client_db):
    mock_response = MagicMock()
    mock_response.data = None
    mock_client_db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_response

    response = client.post('/user/login', json={
        'email': 'nonexistent@example.com',
        'password': 'password123'
    })

    assert response.status_code == 200
    data = response.json()
    assert data['authenticated'] == False
    assert data['message'] == 'User not found'

def test_login_invalid_password(mock_client_db):
    mock_user = {
        'user_id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'password_hash': '$argon2id$v=19$m=65536,t=3,p=4$...'
    }    
    mock_response = MagicMock()
    mock_response.data = mock_user    
    mock_client_db.table.return_value.select.return_value.maybe_single.return_value.execute.return_value = mock_response

    with patch('argon2.PasswordHasher.verify', side_effect=Exception('Invalid password')):
        response = client.post('/user/login', json={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })

        assert response.status_code == 200
        data = response.json()
        assert data['authenticated'] == False
        assert 'error' in data or 'message' in data