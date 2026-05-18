import pytest
import jwt
from utils.auth import hash_password, verify_password, create_access_token, SECRET_KEY

def test_password_hashing():
    password = "StrongPassword123"
    hashed = hash_password(password)
    
    assert password != hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False

def test_create_access_token():
    data = {"user_id": 1, "email": "test@example.com"}
    token = create_access_token(data)
    
    # Verify decoding works
    decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert decoded["user_id"] == 1
    assert decoded["email"] == "test@example.com"
    assert "exp" in decoded

def test_expired_token(monkeypatch):
    data = {"user_id": 1, "email": "test@example.com"}
    
    # Mock ACCESS_TOKEN_EXPIRE_HOURS to negative to ensure token expires immediately
    monkeypatch.setattr('utils.auth.ACCESS_TOKEN_EXPIRE_HOURS', -1)
    expired_token = create_access_token(data)
    
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(expired_token, SECRET_KEY, algorithms=["HS256"])


def test_token_has_jti_claim():
    """Fix 3: Every new token must include a unique jti claim for revocation support."""
    data = {"user_id": 1, "email": "user@test.com"}
    token = create_access_token(data)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    assert "jti" in decoded, "Token must contain a jti claim for revocation support"
    assert len(decoded["jti"]) > 0


def test_revoke_token_blocks_reuse():
    """Fix 3: Once a jti is added to Redis denylist, the token must be effectively revoked."""
    from utils.auth import redis_client, revoke_token
    data = {"user_id": "abc", "email": "user@test.com"}
    token = create_access_token(data)
    decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    jti = decoded["jti"]

    # Token should NOT be in denylist yet
    assert redis_client.exists(f"denylist:{jti}") == 0

    # Revoke it
    revoke_token(jti)
    assert redis_client.exists(f"denylist:{jti}") == 1

    # Clean up
    redis_client.delete(f"denylist:{jti}")

