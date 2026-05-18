import pytest
from crypto_utils import derive_key, aes_encrypt, aes_decrypt, xor_encrypt_decrypt, generate_key_pair, sign_data, verify_signature

def test_derive_key_consistency():
    key1 = derive_key("MySuperSecret")
    key2 = derive_key("MySuperSecret")
    assert key1 == key2

def test_derive_key_different_inputs():
    key1 = derive_key("Password123")
    key2 = derive_key("Password124")
    assert key1 != key2

def test_aes_encryption_decryption():
    data = b"This is a massive secret payload."
    password = "SecurePassword123!"
    encrypted_data, recovery_token = aes_encrypt(data, password)
    
    # Decrypt with password
    decrypted_data_1 = aes_decrypt(encrypted_data, password, is_token=False)
    assert decrypted_data_1 == data
    
    # Decrypt with token
    decrypted_data_2 = aes_decrypt(encrypted_data, recovery_token, is_token=True)
    assert decrypted_data_2 == data

def test_aes_decryption_failure_wrong_password():
    data = b"Secret"
    password = "CorrectHorse"
    wrong_password = "BatteryStaple"
    encrypted_data, _ = aes_encrypt(data, password)
    
    with pytest.raises(ValueError, match="Incorrect Password|InvalidToken|decryption"):  # noqa
        aes_decrypt(encrypted_data, wrong_password, is_token=False)

def test_xor_fallback():
    data = b"Initial data"
    key = "WeakKey"
    enc = xor_encrypt_decrypt(data, key)
    dec = xor_encrypt_decrypt(enc, key)
    assert data == dec
    assert data != enc

def test_ecdsa_signature_flow():
    priv, pub = generate_key_pair()
    data = b"Sign this secure payload"
    
    signature = sign_data(data, priv)
    assert signature != b""
    
    is_valid = verify_signature(data, signature, pub)
    assert is_valid is True

def test_ecdsa_signature_tampering():
    priv, pub = generate_key_pair()
    data = b"Important"
    signature = sign_data(data, priv)
    
    tampered_data = b"Important!"
    is_valid = verify_signature(tampered_data, signature, pub)
    assert is_valid is False
