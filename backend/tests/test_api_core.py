import pytest
import io
import json
from unittest.mock import patch, MagicMock
from app import app
from PIL import Image

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def generate_dummy_image():
    img = Image.new('RGB', (100, 100), color='blue')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

@patch('utils.auth.jwt.decode')
def test_embed_api_valid_token_missing_files(mock_jwt, client):
    """
    With a valid JWT (mocked), token_required passes.
    Next layer hits @require_credits (DB check) → result is NOT 401.
    Confirms auth boundary is working and the middleware chain is correct.
    """
    mock_jwt.return_value = {"user_id": "00000000-0000-0000-0000-000000000001", "email": "test@example.com"}

    response = client.post(
        '/api/embed',
        headers={"Authorization": "Bearer MOCKED_VALID_TOKEN"},
        data={},
        content_type='multipart/form-data'
    )
    # Auth passed (not 401). It hits require_credits or file check → 400/402/500 are acceptable
    assert response.status_code != 401, (
        f"Expected authenticated path (not 401), got {response.status_code}"
    )

def test_embed_api_missing_auth_header(client):
    """
    Without Authorization header, @token_required fires first → 401.
    """
    response = client.post(
        '/api/embed',
        data={},
        content_type='multipart/form-data'
    )
    # No auth header → 401 (token_required fires before file validation)
    assert response.status_code == 401

def test_embed_api_unauthorized(client):
    """Same as above: no token = 401."""
    response = client.post(
        '/api/embed',
        data={'method': 'LSB'},
        content_type='multipart/form-data'
    )
    assert response.status_code == 401
