import pytest
import json
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('routes.auth.SessionLocal')
def test_signup_success(mock_session, client):
    # Mocking the DB session
    mock_db = mock_session.return_value
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    payload = {
        "email": "newuser@example.com",
        "password": "SecurePassword123!"
    }
    
    response = client.post('/api/auth/signup', json=payload)
    data = json.loads(response.data)
    
    assert response.status_code == 201
    assert data["success"] is True
    assert "User created" in data["data"]["message"]

@patch('routes.auth.SessionLocal')
def test_signup_duplicate_email(mock_session, client):
    mock_db = mock_session.return_value
    # Simulate user exists
    mock_db.query.return_value.filter.return_value.first.return_value = True 
    
    payload = {
        "email": "existing@example.com",
        "password": "SecurePassword123!"
    }
    
    response = client.post('/api/auth/signup', json=payload)
    data = json.loads(response.data)
    
    assert response.status_code == 400
    assert data["success"] is False
    assert data["error"] == "Email already registered"

@patch('routes.auth.verify_password')
@patch('routes.auth.SessionLocal')
def test_login_success(mock_session, mock_verify, client):
    mock_db = mock_session.return_value
    mock_user = mock_db.query.return_value.filter.return_value.first.return_value
    mock_user.email = "user@example.com"
    mock_user.is_verified = True
    mock_user.id = "1234-5678"
    mock_user.to_dict.return_value = {"id": "1234-5678", "email": "user@example.com"}
    
    mock_verify.return_value = True
    
    payload = {
        "email": "user@example.com",
        "password": "CorrectPassword"
    }
    
    response = client.post('/api/auth/login', json=payload)
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data["success"] is True
    assert "access_token" in data["data"]

def test_login_missing_payload(client):
    response = client.post('/api/auth/login', json={})
    assert response.status_code == 400
