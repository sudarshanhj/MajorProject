import pytest
import json
from unittest.mock import patch
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@patch('routes.razorpay_routes.client.order.create')
@patch('utils.auth.jwt.decode')
def test_create_order_success(mock_jwt, mock_order_create, client):
    mock_jwt.return_value = {"user_id": "123", "email": "test@example.com"}
    mock_order_create.return_value = {
        "id": "order_12345",
        "amount": 9900,
        "currency": "INR"
    }
    
    payload = {"amount_inr": 99}
    
    response = client.post(
        '/api/razorpay/create-order',
        json=payload,
        headers={"Authorization": "Bearer TOKEN"}
    )
    data = json.loads(response.data)
    
    assert response.status_code == 200
    assert data["success"] is True
    assert data["data"]["order_id"] == "order_12345"

@patch('utils.auth.jwt.decode')
def test_create_order_invalid_amount(mock_jwt, client):
    mock_jwt.return_value = {"user_id": "123", "email": "test@example.com"}
    
    payload = {"amount_inr": 50} # 50 is not in PRICING_TIERS
    
    response = client.post('/api/razorpay/create-order', json=payload, headers={"Authorization": "Bearer TOKEN"})
    data = json.loads(response.data)
    
    assert response.status_code == 400
    assert data["error"] == "Invalid pricing tier"

def test_webhook_missing_signature(client):
    payload = {"event": "payment.captured"}
    
    response = client.post('/api/razorpay/webhook', json=payload)
    data = json.loads(response.data)
    
    assert response.status_code == 400
    assert data["error"] == "Missing signature headers"
