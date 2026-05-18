"""
═══════════════════════════════════════════════════════════════════
DEEPSTEGAI V2 — PHASE 1: UNIT TEST DOMINATION
Module: Cryptographic Pipeline (AES-256 / SHA-256 / ECDSA)
Coverage Target: 100%
Author: Antigravity QA Engine
Standard: Ian Somerville Testing Model
═══════════════════════════════════════════════════════════════════
"""

import pytest
import os
import sys
import secrets
import struct
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_utils import (
    derive_key,
    aes_encrypt,
    aes_decrypt,
    xor_encrypt_decrypt,
    generate_key_pair,
    sign_data,
    verify_signature,
)


# ─────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_data():
    return b"DeepStegAI_UNIT_TEST_PAYLOAD_SECURE_12345"


@pytest.fixture
def strong_password():
    return "Str0ng!P@ss#DeepSteg2026"


@pytest.fixture
def ecdsa_keypair():
    priv, pub = generate_key_pair()
    return priv, pub


# ─────────────────────────────────────────────────────────────────
# SECTION 1: KEY DERIVATION (PBKDF2-SHA256)
# ─────────────────────────────────────────────────────────────────

class TestKeyDerivation:
    """Tests for PBKDF2HMAC key derivation — determinism, uniqueness, format."""

    def test_key_derivation_is_deterministic(self, strong_password):
        """Same password must always produce identical key."""
        key1 = derive_key(strong_password)
        key2 = derive_key(strong_password)
        assert key1 == key2, "Key derivation must be deterministic for same password"

    def test_key_derivation_different_passwords_produce_different_keys(self):
        """Different passwords must never produce the same key."""
        k1 = derive_key("PasswordAlpha")
        k2 = derive_key("PasswordBeta")
        assert k1 != k2, "Collision detected: two distinct passwords produced the same key"

    def test_key_derivation_returns_bytes(self, strong_password):
        """Key must be bytes (base64 URL-safe encoded)."""
        key = derive_key(strong_password)
        assert isinstance(key, bytes), "derive_key must return bytes"

    def test_key_derivation_length_is_44(self, strong_password):
        """Fernet key is 32 raw bytes → 44 url-safe base64 chars."""
        key = derive_key(strong_password)
        assert len(key) == 44, f"Expected 44-byte Fernet key, got {len(key)}"

    def test_key_derivation_empty_password(self):
        """Empty password must still produce a valid key (not crash)."""
        key = derive_key("")
        assert isinstance(key, bytes) and len(key) == 44

    def test_key_derivation_unicode_password(self):
        """Unicode passwords (international chars) must work without error."""
        key = derive_key("密码SecureAI🔐")
        assert isinstance(key, bytes) and len(key) == 44

    def test_key_derivation_very_long_password(self):
        """Extremely long password must not crash or truncate incorrectly."""
        key = derive_key("A" * 10000)
        assert isinstance(key, bytes) and len(key) == 44

    def test_key_derivation_special_characters(self):
        """Special characters in password must be handled safely."""
        key = derive_key("!@#$%^&*(){}[]|\\/<>~`±§")
        assert isinstance(key, bytes) and len(key) == 44


# ─────────────────────────────────────────────────────────────────
# SECTION 2: AES-256 (FERNET) ENCRYPTION / DECRYPTION
# ─────────────────────────────────────────────────────────────────

class TestAESEncryption:
    """Full round-trip AES-256 encryption-decryption tests."""

    def test_encrypt_returns_encrypted_bytes_and_token(self, sample_data, strong_password):
        encrypted, token = aes_encrypt(sample_data, strong_password)
        assert isinstance(encrypted, bytes), "Encrypted data must be bytes"
        assert isinstance(token, str), "Recovery token must be a string"
        assert encrypted != sample_data, "Ciphertext must differ from plaintext"

    def test_round_trip_via_password(self, sample_data, strong_password):
        """Encrypt → Decrypt via password must recover original exactly."""
        encrypted, _ = aes_encrypt(sample_data, strong_password)
        decrypted = aes_decrypt(encrypted, strong_password, is_token=False)
        assert decrypted == sample_data, "Round-trip via password failed"

    def test_round_trip_via_token(self, sample_data, strong_password):
        """Encrypt → Decrypt via recovery token must recover original exactly."""
        encrypted, token = aes_encrypt(sample_data, strong_password)
        decrypted = aes_decrypt(encrypted, token, is_token=True)
        assert decrypted == sample_data, "Round-trip via token failed"

    def test_wrong_password_raises_value_error(self, sample_data, strong_password):
        """Incorrect password must raise ValueError, not silently return garbage."""
        encrypted, _ = aes_encrypt(sample_data, strong_password)
        with pytest.raises(ValueError):
            aes_decrypt(encrypted, "WrongPassword!", is_token=False)

    def test_tampered_ciphertext_raises_value_error(self, sample_data, strong_password):
        """Bitflip in ciphertext must trigger Fernet MAC failure → ValueError."""
        encrypted, _ = aes_encrypt(sample_data, strong_password)
        tampered = bytearray(encrypted)
        tampered[20] ^= 0xFF  # Corrupt a byte in the middle
        with pytest.raises(ValueError):
            aes_decrypt(bytes(tampered), strong_password, is_token=False)

    def test_empty_plaintext_encrypt_decrypt(self, strong_password):
        """Empty payload must encrypt/decrypt correctly."""
        encrypted, token = aes_encrypt(b"", strong_password)
        decrypted = aes_decrypt(encrypted, strong_password, is_token=False)
        assert decrypted == b""

    def test_single_byte_payload(self, strong_password):
        """Single byte payload must round-trip correctly."""
        data = b"\x00"
        encrypted, _ = aes_encrypt(data, strong_password)
        decrypted = aes_decrypt(encrypted, strong_password, is_token=False)
        assert decrypted == data

    def test_large_payload_1mb(self, strong_password):
        """1 MB binary payload must encrypt and decrypt without memory failure."""
        data = secrets.token_bytes(1024 * 1024)
        encrypted, token = aes_encrypt(data, strong_password)
        decrypted = aes_decrypt(encrypted, token, is_token=True)
        assert decrypted == data

    def test_same_plaintext_produces_different_ciphertexts(self, sample_data, strong_password):
        """Fernet uses random IVs — same plaintext encrypted twice differs."""
        enc1, _ = aes_encrypt(sample_data, strong_password)
        enc2, _ = aes_encrypt(sample_data, strong_password)
        assert enc1 != enc2, "AES must be non-deterministic (random IV required)"

    def test_binary_data_encrypt_decrypt(self, strong_password):
        """Random binary bytes (not UTF-8) must round-trip correctly."""
        data = bytes(range(256)) * 4
        encrypted, _ = aes_encrypt(data, strong_password)
        decrypted = aes_decrypt(encrypted, strong_password, is_token=False)
        assert decrypted == data

    def test_null_bytes_in_payload(self, strong_password):
        """Null bytes embedded in payload must not be stripped."""
        data = b"\x00" * 100 + b"SECRET" + b"\x00" * 100
        encrypted, token = aes_encrypt(data, strong_password)
        decrypted = aes_decrypt(encrypted, token, is_token=True)
        assert decrypted == data

    @pytest.mark.parametrize("size", [1, 16, 32, 64, 128, 512, 1024, 65536])
    def test_various_payload_sizes(self, strong_password, size):
        """Parametrized: test encryption across many payload sizes."""
        data = secrets.token_bytes(size)
        encrypted, token = aes_encrypt(data, strong_password)
        decrypted = aes_decrypt(encrypted, token, is_token=True)
        assert decrypted == data


# ─────────────────────────────────────────────────────────────────
# SECTION 3: SHA-256 INTEGRITY (CHECKSUM)
# ─────────────────────────────────────────────────────────────────

class TestSHA256Integrity:
    """Validates SHA-256 checksum via protocol.py's calculate_checksum."""

    def setup_method(self):
        from protocol import calculate_checksum
        self.calc = calculate_checksum

    def test_checksum_produces_32_bytes(self):
        c = self.calc(b"test data")
        assert len(c) == 32

    def test_checksum_is_deterministic(self):
        data = b"reproducible_data"
        assert self.calc(data) == self.calc(data)

    def test_checksum_differs_for_different_data(self):
        assert self.calc(b"data_A") != self.calc(b"data_B")

    def test_checksum_empty_data(self):
        """SHA-256 of empty string is a valid, well-known value."""
        c = self.calc(b"")
        assert len(c) == 32
        # SHA256("") = e3b0c44298fc1c14...
        assert c == hashlib.sha256(b"").digest()

    def test_checksum_large_data(self):
        data = b"X" * (10 * 1024 * 1024)  # 10 MB
        c = self.calc(data)
        assert len(c) == 32

    def test_bitflip_changes_checksum(self):
        data = bytearray(b"original_payload_data_12345")
        c1 = self.calc(bytes(data))
        data[5] ^= 0x01
        c2 = self.calc(bytes(data))
        assert c1 != c2


# ─────────────────────────────────────────────────────────────────
# SECTION 4: XOR FALLBACK
# ─────────────────────────────────────────────────────────────────

class TestXORFallback:
    """Tests for the XOR fallback encryption (when cryptography lib unavailable)."""

    def test_xor_is_symmetric(self, sample_data):
        key = "FallbackKey"
        enc = xor_encrypt_decrypt(sample_data, key)
        dec = xor_encrypt_decrypt(enc, key)
        assert dec == sample_data

    def test_xor_ciphertext_differs_from_plaintext(self, sample_data):
        enc = xor_encrypt_decrypt(sample_data, "SomeKey")
        assert enc != sample_data

    def test_xor_empty_data(self):
        result = xor_encrypt_decrypt(b"", "key")
        assert result == b""

    def test_xor_different_keys_produce_different_output(self, sample_data):
        enc1 = xor_encrypt_decrypt(sample_data, "KeyA")
        enc2 = xor_encrypt_decrypt(sample_data, "KeyB")
        assert enc1 != enc2

    def test_xor_single_char_key(self):
        data = b"Hello World"
        enc = xor_encrypt_decrypt(data, "K")
        dec = xor_encrypt_decrypt(enc, "K")
        assert dec == data

    def test_xor_key_wraps_around(self):
        """Key must cycle when shorter than data."""
        data = b"A" * 100
        enc = xor_encrypt_decrypt(data, "short")
        dec = xor_encrypt_decrypt(enc, "short")
        assert dec == data


# ─────────────────────────────────────────────────────────────────
# SECTION 5: ECDSA DIGITAL SIGNATURES
# ─────────────────────────────────────────────────────────────────

class TestECDSASignatures:
    """Tests for ECDSA key generation, signing, and verification."""

    def test_key_generation_returns_pem_bytes(self, ecdsa_keypair):
        priv, pub = ecdsa_keypair
        assert priv.startswith(b"-----BEGIN PRIVATE KEY-----")
        assert pub.startswith(b"-----BEGIN PUBLIC KEY-----")

    def test_sign_produces_non_empty_signature(self, ecdsa_keypair, sample_data):
        priv, _ = ecdsa_keypair
        sig = sign_data(sample_data, priv)
        assert isinstance(sig, bytes)
        assert len(sig) > 0

    def test_signature_verifies_correctly(self, ecdsa_keypair, sample_data):
        priv, pub = ecdsa_keypair
        sig = sign_data(sample_data, priv)
        assert verify_signature(sample_data, sig, pub) is True

    def test_tampered_data_fails_verification(self, ecdsa_keypair, sample_data):
        priv, pub = ecdsa_keypair
        sig = sign_data(sample_data, priv)
        tampered = sample_data + b"TAMPERED"
        assert verify_signature(tampered, sig, pub) is False

    def test_tampered_signature_fails_verification(self, ecdsa_keypair, sample_data):
        priv, pub = ecdsa_keypair
        sig = sign_data(sample_data, priv)
        bad_sig = bytearray(sig)
        bad_sig[5] ^= 0xFF
        assert verify_signature(sample_data, bytes(bad_sig), pub) is False

    def test_wrong_key_pair_fails_verification(self, sample_data):
        priv1, _ = generate_key_pair()
        _, pub2 = generate_key_pair()
        sig = sign_data(sample_data, priv1)
        # Signature from key1 should NOT verify with pub2
        assert verify_signature(sample_data, sig, pub2) is False

    def test_unique_keys_per_generation(self):
        priv1, pub1 = generate_key_pair()
        priv2, pub2 = generate_key_pair()
        assert priv1 != priv2
        assert pub1 != pub2

    def test_sign_empty_data(self):
        priv, pub = generate_key_pair()
        sig = sign_data(b"", priv)
        assert verify_signature(b"", sig, pub) is True

    def test_sign_large_data(self):
        priv, pub = generate_key_pair()
        data = secrets.token_bytes(100000)
        sig = sign_data(data, priv)
        assert verify_signature(data, sig, pub) is True

    def test_sign_with_string_key(self, sample_data):
        """sign_data must accept PEM key as string, not just bytes."""
        priv, pub = generate_key_pair()
        priv_str = priv.decode('utf-8')
        pub_str = pub.decode('utf-8')
        sig = sign_data(sample_data, priv_str)
        assert verify_signature(sample_data, sig, pub_str) is True


# ─────────────────────────────────────────────────────────────────
# SECTION 6: FUZZ TESTING
# ─────────────────────────────────────────────────────────────────

class TestFuzzCrypto:
    """Fuzz-style tests: send random inputs and guarantee no crashes."""

    @pytest.mark.parametrize("_", range(10))
    def test_fuzz_aes_random_payloads(self, _):
        """Random payloads of random lengths must not crash encryption."""
        size = secrets.randbelow(1024) + 1
        data = secrets.token_bytes(size)
        password = secrets.token_hex(16)
        encrypted, token = aes_encrypt(data, password)
        decrypted = aes_decrypt(encrypted, token, is_token=True)
        assert decrypted == data

    @pytest.mark.parametrize("_", range(5))
    def test_fuzz_wrong_token_always_raises(self, _):
        """Random wrong token must always raise, never silently corrupt."""
        data = b"SomeSecret"
        encrypted, _ = aes_encrypt(data, "correct_pass")
        # Generate random junk token of correct length
        junk_token = secrets.token_urlsafe(44)
        with pytest.raises(Exception):  # Can be ValueError or InvalidToken
            aes_decrypt(encrypted, junk_token, is_token=True)

    @pytest.mark.parametrize("_", range(5))
    def test_fuzz_xor_random_sizes(self, _):
        """Random XOR should always be losslessly reversible."""
        size = secrets.randbelow(500) + 1
        data = secrets.token_bytes(size)
        key = secrets.token_hex(secrets.randbelow(20) + 1)
        assert xor_encrypt_decrypt(xor_encrypt_decrypt(data, key), key) == data
