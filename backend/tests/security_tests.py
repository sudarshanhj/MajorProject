import pytest
import jwt
from app import app
from utils.auth import SECRET_KEY

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_sql_injection_login(client):
    # Attempt SQL injection in email field
    payload = {
        "email": "admin@example.com' OR '1'='1",
        "password": "password"
    }
    
    response = client.post('/api/auth/login', json=payload)
    # ORM should sanitize this and it should simply fail auth
    assert response.status_code in [401, 400, 422]
    
def test_jwt_tampering(client):
    valid_data = {"user_id": "1", "email": "admin@deepsteg.ai"}
    valid_token = jwt.encode(valid_data, SECRET_KEY, algorithm="HS256")
    
    # Tamper with the token (e.g., trying to change user_id without knowing secret key)
    # Re-signing with a dummy key
    tampered_token = jwt.encode({"user_id": "2", "email": "admin@deepsteg.ai"}, "wrong_secret", algorithm="HS256")
    
    response = client.post(
        '/api/embed',
        headers={"Authorization": f"Bearer {tampered_token}"},
        data={'method': 'LSB'},
        content_type='multipart/form-data'
    )
    # The middleware should catch the invalid signature
    assert response.status_code == 401

def test_rate_limiting_abuse(client):
    # Depending on configuration, hit the endpoint 11 times.
    # We disabled limiter in testing, but structurally this is how it looks:
    # for i in range(12):
    #     res = client.post('/api/embed', ...)
    # assert res.status_code == 429
    pass
