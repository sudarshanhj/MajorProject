"""
═══════════════════════════════════════════════════════════════════
DEEPSTEGAI V2 — PHASE 1: UNIT TEST DOMINATION
Module: Steganography Engine (LSB + Capacity + Protocol V1)
Coverage Target: 100% for stego_engine.py, protocol.py
Author: Antigravity QA Engine
Standard: Ian Somerville Testing Model
═══════════════════════════════════════════════════════════════════
"""

import pytest
import io
import os
import sys
import struct
import secrets
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego_engine import (
    bytes_to_bits,
    bits_to_bytes,
    image_capacity_bits,
    embed_payload_into_image,
    extract_payload_from_image,
    MAGIC,
    HEADER_LEN,
)
from protocol import package_payload, unpackage_payload, calculate_checksum, SIGNATURE


# ─────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────

def make_image(w=200, h=200, color="red"):
    return Image.new("RGB", (w, h), color=color)


def make_valid_lsb_payload(secret_data: bytes, filename: str = "test.txt", password: str = None):
    """Uses the canonical protocol packager to build a valid payload."""
    return package_payload([{"name": filename, "data": secret_data}], "LSB", password)


@pytest.fixture
def small_image():
    return make_image(100, 100)


@pytest.fixture
def large_image():
    return make_image(500, 500)


@pytest.fixture
def tiny_image():
    """Barely enough pixels for a header — minimal boundary image."""
    return make_image(10, 10)


@pytest.fixture
def secret_payload():
    return b"DeepStegAI_SECRET_TEST_PAYLOAD_v2"


# ─────────────────────────────────────────────────────────────────
# SECTION 1: BIT CONVERSION CORRECTNESS
# ─────────────────────────────────────────────────────────────────

class TestBitConversion:
    """Tests for bytes_to_bits and bits_to_bytes — the foundation of LSB."""

    def test_bytes_to_bits_known_value(self):
        """b'A' = 0x41 = 01000001 in binary."""
        result = bytes_to_bits(b"A")
        expected = np.array([0, 1, 0, 0, 0, 0, 0, 1], dtype=np.uint8)
        np.testing.assert_array_equal(result, expected)

    def test_bits_to_bytes_known_value(self):
        bits = np.array([0, 1, 0, 0, 0, 0, 0, 1], dtype=np.uint8)
        result = bits_to_bytes(bits, nbytes=1)
        assert result == b"A"

    def test_round_trip_single_byte(self):
        for b_val in range(256):
            data = bytes([b_val])
            assert bits_to_bytes(bytes_to_bits(data), 1) == data

    def test_round_trip_arbitrary_bytes(self):
        data = b"Hello, DeepStegAI! 123 !@#"
        recovered = bits_to_bytes(bytes_to_bits(data), len(data))
        assert recovered == data

    def test_round_trip_binary_data(self):
        data = bytes(range(256))
        recovered = bits_to_bytes(bytes_to_bits(data), len(data))
        assert recovered == data

    def test_bits_to_bytes_zero_pads_partial_bits(self):
        """If bit count is not multiple of 8, last byte should be zero-padded."""
        bits = np.array([1, 0, 0, 0, 0, 0, 0], dtype=np.uint8)  # 7 bits
        result = bits_to_bytes(bits)
        assert result is not None and len(result) == 1

    @pytest.mark.parametrize("size", [1, 10, 100, 1000, 10000])
    def test_round_trip_various_sizes(self, size):
        data = secrets.token_bytes(size)
        recovered = bits_to_bytes(bytes_to_bits(data), size)
        assert recovered == data


# ─────────────────────────────────────────────────────────────────
# SECTION 2: CAPACITY CALCULATOR (STRICT 35% RULE)
# ─────────────────────────────────────────────────────────────────

class TestCapacityCalculator:
    """
    Validates image_capacity_bits AND the 35% security policy.
    35% rule: max_payload_bytes = floor(cover_file_bytes * 0.35)
    """

    def test_capacity_100x100_image(self, small_image):
        """100×100 RGB → 30,000 bits capacity."""
        assert image_capacity_bits(small_image) == 30_000

    def test_capacity_500x500_image(self, large_image):
        assert image_capacity_bits(large_image) == 750_000

    def test_capacity_1x1_image(self):
        img = make_image(1, 1)
        assert image_capacity_bits(img) == 3

    @pytest.mark.parametrize("w, h", [(64, 64), (128, 128), (256, 256), (1920, 1080)])
    def test_capacity_formula_wh3(self, w, h):
        img = make_image(w, h)
        assert image_capacity_bits(img) == w * h * 3

    def test_35_percent_rule_enforced(self):
        """Verifies the app-level 35% limit via the calculate_max_payload helper."""
        import math
        SECURITY_LIMIT_RATIO = 0.35
        cover_sizes = [1000, 10000, 100000, 1048576, 5242880]
        for cover_bytes in cover_sizes:
            expected = math.floor(cover_bytes * SECURITY_LIMIT_RATIO)
            from app import calculate_max_payload
            result = calculate_max_payload(cover_bytes)
            assert result == expected, f"35% rule broken for {cover_bytes} bytes"

    def test_zero_cover_size_returns_zero(self):
        import math
        from app import calculate_max_payload
        assert calculate_max_payload(0) == 0

    def test_capacity_bits_is_always_multiple_of_3(self):
        """Width * Height * 3 is always divisible by 3."""
        for w, h in [(100, 100), (77, 53), (1024, 768)]:
            assert image_capacity_bits(make_image(w, h)) % 3 == 0


# ─────────────────────────────────────────────────────────────────
# SECTION 3: LSB EMBEDDING / EXTRACTION
# ─────────────────────────────────────────────────────────────────

class TestLSBEmbedExtract:
    """Tests for embed_payload_into_image and extract_payload_from_image."""

    def test_embed_changes_image(self, small_image, secret_payload):
        payload = make_valid_lsb_payload(secret_payload)
        stego = embed_payload_into_image(small_image, payload)
        orig_arr = np.array(small_image)
        stego_arr = np.array(stego)
        assert not np.array_equal(orig_arr, stego_arr), "Embedding should modify pixels"

    def test_stego_image_is_valid_pil(self, small_image, secret_payload):
        payload = make_valid_lsb_payload(secret_payload)
        stego = embed_payload_into_image(small_image, payload)
        assert isinstance(stego, Image.Image)
        assert stego.size == small_image.size
        assert stego.mode == "RGB"

    def test_embed_extract_round_trip(self, large_image, secret_payload):
        """Full round-trip: embed → extract → unpackage → verify bit-perfect."""
        payload = make_valid_lsb_payload(secret_payload)
        stego = embed_payload_into_image(large_image, payload)
        _, raw_block, _ = extract_payload_from_image(stego)
        results, is_bundle = unpackage_payload(raw_block, password=None)
        assert results[0]["data"] == secret_payload

    def test_embed_extract_with_password(self, large_image, secret_payload):
        """Encrypted LSB embed must round-trip with password decrypt."""
        password = "EncryptThisV2!"
        payload = make_valid_lsb_payload(secret_payload, password=password)
        stego = embed_payload_into_image(large_image, payload)
        _, raw_block, _ = extract_payload_from_image(stego)
        results, _ = unpackage_payload(raw_block, password=password)
        assert results[0]["data"] == secret_payload

    def test_extract_without_password_on_encrypted_payload_fails(self, large_image, secret_payload):
        """Encrypted payload without supplying password must raise ValueError."""
        payload = make_valid_lsb_payload(secret_payload, password="APassword")
        stego = embed_payload_into_image(large_image, payload)
        _, raw_block, _ = extract_payload_from_image(stego)
        with pytest.raises(ValueError):
            unpackage_payload(raw_block, password=None)

    def test_embed_too_large_payload_raises(self, small_image):
        """Payload exceeding image pixel capacity must raise ValueError."""
        huge_payload = b"X" * 4000  # 100x100 = 3750 bytes capacity
        with pytest.raises(ValueError, match="too large"):
            embed_payload_into_image(small_image, huge_payload)

    def test_extract_from_clean_image_raises(self, small_image):
        """Extracting from unmodified image with no magic bytes must raise."""
        with pytest.raises(ValueError, match="valid DeepStegAI header"):
            extract_payload_from_image(small_image)

    def test_lsb_only_modifies_last_bit(self, small_image, secret_payload):
        """LSB embedding must not change any pixel value by more than 1."""
        payload = make_valid_lsb_payload(secret_payload)
        stego = embed_payload_into_image(small_image, payload)
        diff = np.abs(np.array(small_image).astype(int) - np.array(stego).astype(int))
        assert diff.max() <= 1, "LSB violation: pixel changed by more than 1"

    def test_embed_maintains_image_dimensions(self, large_image, secret_payload):
        payload = make_valid_lsb_payload(secret_payload)
        stego = embed_payload_into_image(large_image, payload)
        assert stego.size == large_image.size

    def test_minimum_viable_payload(self, large_image):
        """1-byte payload must embed/extract correctly."""
        payload = make_valid_lsb_payload(b"\x42")
        stego = embed_payload_into_image(large_image, payload)
        _, raw_block, _ = extract_payload_from_image(stego)
        results, _ = unpackage_payload(raw_block, password=None)
        assert results[0]["data"] == b"\x42"

    @pytest.mark.parametrize("data_size", [1, 10, 100, 500, 1000, 2000])
    def test_parametrized_payload_sizes(self, large_image, data_size):
        """Multiple payload sizes must all embed/extract correctly."""
        secret = secrets.token_bytes(data_size)
        payload = make_valid_lsb_payload(secret, filename=f"file_{data_size}.bin")
        stego = embed_payload_into_image(large_image, payload)
        _, raw_block, _ = extract_payload_from_image(stego)
        results, _ = unpackage_payload(raw_block, password=None)
        assert results[0]["data"] == secret


# ─────────────────────────────────────────────────────────────────
# SECTION 4: DEEPSTEGAI_V1 PROTOCOL — PACKAGE / UNPACKAGE
# ─────────────────────────────────────────────────────────────────

class TestProtocolV1:
    """Tests for the DEEPSTEGAI_V1 protocol packaging/unpackaging."""

    def test_package_starts_with_signature(self, secret_payload):
        block = package_payload([{"name": "test.txt", "data": secret_payload}], "LSB")
        assert block.startswith(SIGNATURE)

    def test_package_ends_with_32_byte_checksum(self, secret_payload):
        block = package_payload([{"name": "test.txt", "data": secret_payload}], "LSB")
        checksum = block[-32:]
        expected = calculate_checksum(block[:-32])
        assert checksum == expected, "Checksum mismatch at end of package"

    def test_unpackage_single_file(self, secret_payload):
        block = package_payload([{"name": "secret.txt", "data": secret_payload}], "LSB")
        results, is_bundle = unpackage_payload(block)
        assert not is_bundle
        assert results[0]["name"] == "secret.txt"
        assert results[0]["data"] == secret_payload

    def test_unpackage_multi_file_bundle(self):
        """Multiple files are automatically zipped and returned as bundle."""
        files = [
            {"name": "a.txt", "data": b"File A content"},
            {"name": "b.txt", "data": b"File B content"},
        ]
        block = package_payload(files, "LSB")
        results, is_bundle = unpackage_payload(block)
        assert is_bundle
        names = [r["name"] for r in results]
        assert "a.txt" in names
        assert "b.txt" in names

    def test_unpackage_with_correct_password(self, secret_payload):
        block = package_payload([{"name": "enc.txt", "data": secret_payload}], "LSB", password="GoodPass")
        results, _ = unpackage_payload(block, password="GoodPass")
        assert results[0]["data"] == secret_payload

    def test_unpackage_with_wrong_password_raises(self, secret_payload):
        block = package_payload([{"name": "enc.txt", "data": secret_payload}], "LSB", password="GoodPass")
        with pytest.raises(ValueError):
            unpackage_payload(block, password="WrongPass")

    def test_unpackage_corrupted_checksum_raises(self, secret_payload):
        """Bit flip in checksum region must fail — raises any ValueError."""
        block = bytearray(package_payload([{"name": "t.txt", "data": secret_payload}], "LSB"))
        block[-5] ^= 0xFF  # Corrupt checksum
        with pytest.raises(ValueError, match="Incorrect password|credentials"):
            unpackage_payload(bytes(block))

    def test_unpackage_corrupted_payload_raises(self, secret_payload):
        """Bit flip in payload body region must fail checksum — raises any ValueError."""
        block = bytearray(package_payload([{"name": "t.txt", "data": secret_payload}], "LSB"))
        # Corrupt one byte in the payload area (after header, before checksum)
        midpoint = len(block) // 2
        block[midpoint] ^= 0xFF
        with pytest.raises(ValueError, match="Incorrect password|credentials"):
            unpackage_payload(bytes(block))

    def test_unpackage_missing_signature_raises(self, secret_payload):
        """Data not starting with SIGNATURE must immediately raise."""
        with pytest.raises(ValueError, match="No Signature Detected"):
            unpackage_payload(b"GARBAGE_DATA_NO_SIGNATURE_HERE")

    def test_package_protocol_flag_lsb(self, secret_payload):
        block = package_payload([{"name": "t.bin", "data": secret_payload}], "LSB")
        # Proto byte is at offset 13 (after 13-byte signature)
        proto_id = block[13]
        assert proto_id == 0  # 0 = LSB

    def test_package_protocol_flag_adaptive(self, secret_payload):
        block = package_payload([{"name": "t.bin", "data": secret_payload}], "ADAPTIVE")
        proto_id = block[13]
        assert proto_id == 1  # 1 = Adaptive

    def test_package_encryption_flag_set_when_password(self, secret_payload):
        block = package_payload([{"name": "t.bin", "data": secret_payload}], "LSB", password="pass")
        enc_flag = block[14]
        assert enc_flag == 1

    def test_package_encryption_flag_clear_when_no_password(self, secret_payload):
        block = package_payload([{"name": "t.bin", "data": secret_payload}], "LSB")
        enc_flag = block[14]
        assert enc_flag == 0

    def test_empty_payload(self):
        block = package_payload([{"name": "empty.bin", "data": b""}], "LSB")
        results, _ = unpackage_payload(block)
        assert results[0]["data"] == b""

    def test_binary_payload(self):
        data = bytes(range(256)) * 10
        block = package_payload([{"name": "binary.bin", "data": data}], "LSB")
        results, _ = unpackage_payload(block)
        assert results[0]["data"] == data

    def test_unicode_filename(self):
        data = b"unicode test"
        block = package_payload([{"name": "файл.txt", "data": data}], "LSB")
        results, _ = unpackage_payload(block)
        assert results[0]["name"] == "файл.txt"
        assert results[0]["data"] == data


# ─────────────────────────────────────────────────────────────────
# SECTION 5: DETECTION ENGINE
# ─────────────────────────────────────────────────────────────────

class TestDetectionEngine:
    """Tests for scan_image_for_signature."""

    def setup_method(self):
        from detection_engine import scan_image_for_signature
        self.scan = scan_image_for_signature

    def test_clean_image_not_detected(self, small_image):
        result = self.scan(small_image)
        assert result["detected"] is False

    def test_lsb_stego_image_detected(self, large_image, secret_payload):
        payload = make_valid_lsb_payload(secret_payload)
        stego = embed_payload_into_image(large_image, payload)
        result = self.scan(stego)
        assert result["detected"] is True
        assert "LSB" in result["message"] or "Standard" in result["message"]

    def test_detection_result_has_required_keys(self, small_image):
        result = self.scan(small_image)
        assert "detected" in result
        assert "confidence" in result or "message" in result

    def test_tiny_image_does_not_crash(self, tiny_image):
        """Less than 104 pixels — should return gracefully."""
        result = self.scan(tiny_image)
        assert "detected" in result or "error" in result

    def test_monochrome_image_not_detected(self):
        img = Image.new("L", (200, 200), color=128).convert("RGB")
        result = self.scan(img)
        assert result["detected"] is False

    def test_all_black_image_not_detected(self):
        img = Image.new("RGB", (200, 200), color=(0, 0, 0))
        result = self.scan(img)
        assert result["detected"] is False

    def test_all_white_image_not_detected(self):
        img = Image.new("RGB", (200, 200), color=(255, 255, 255))
        result = self.scan(img)
        assert result["detected"] is False


# ─────────────────────────────────────────────────────────────────
# SECTION 6: PIXEL SHUFFLE DETERMINISM
# ─────────────────────────────────────────────────────────────────

class TestPixelShuffleDeterminism:
    """Validates that password-seeded shuffles are deterministic."""

    def test_same_password_same_shuffle(self, large_image, secret_payload):
        """Two embeds with same password must produce identical stego images."""
        from adaptive_engine import embed_file_adaptive
        payload = make_valid_lsb_payload(secret_payload, password="TestPass")
        stego1, _ = embed_file_adaptive(large_image.copy(), payload, "p.bin", "TestPass")
        stego2, _ = embed_file_adaptive(large_image.copy(), payload, "p.bin", "TestPass")
        np.testing.assert_array_equal(np.array(stego1), np.array(stego2))

    def test_different_passwords_different_shuffle(self, large_image, secret_payload):
        """Different passwords must produce different stego images."""
        from adaptive_engine import embed_file_adaptive
        payload = make_valid_lsb_payload(secret_payload, password="PassA")
        stego1, _ = embed_file_adaptive(large_image.copy(), payload, "p.bin", "PassA")
        payload2 = make_valid_lsb_payload(secret_payload, password="PassB")
        stego2, _ = embed_file_adaptive(large_image.copy(), payload2, "p.bin", "PassB")
        assert not np.array_equal(np.array(stego1), np.array(stego2))

    def test_recovery_token_is_deterministic_from_password(self):
        """Same password must yield same recovery token across runs."""
        from adaptive_engine import embed_file_adaptive
        img = make_image(400, 400)
        payload = make_valid_lsb_payload(b"test data", password="MyPass")
        _, tok1 = embed_file_adaptive(img.copy(), payload, "f.bin", "MyPass")
        _, tok2 = embed_file_adaptive(img.copy(), payload, "f.bin", "MyPass")
        assert tok1 == tok2


# ─────────────────────────────────────────────────────────────────
# SECTION 7: ADAPTIVE ENGINE ROUND-TRIP
# ─────────────────────────────────────────────────────────────────

class TestAdaptiveEngineRoundTrip:
    """Tests for embed_file_adaptive and extract_file_adaptive."""

    def test_adaptive_embed_extract_round_trip(self, large_image, secret_payload):
        from adaptive_engine import embed_file_adaptive, extract_file_adaptive
        password = "AdaptivePass123"
        payload = make_valid_lsb_payload(secret_payload, password=password)
        stego, token = embed_file_adaptive(large_image.copy(), payload, "s.bin", password)
        _, raw_block, _ = extract_file_adaptive(stego, password=password)
        results, _ = unpackage_payload(raw_block, password=password)
        assert results[0]["data"] == secret_payload

    def test_adaptive_extract_with_token(self, large_image, secret_payload):
        from adaptive_engine import embed_file_adaptive, extract_file_adaptive
        password = "TokenTest99"
        payload = make_valid_lsb_payload(secret_payload, password=password)
        stego, token = embed_file_adaptive(large_image.copy(), payload, "s.bin", password)
        _, raw_block, _ = extract_file_adaptive(stego, recovery_token=token)
        results, _ = unpackage_payload(raw_block, password=password)
        assert results[0]["data"] == secret_payload

    def test_adaptive_wrong_password_raises(self, large_image, secret_payload):
        from adaptive_engine import embed_file_adaptive, extract_file_adaptive
        payload = make_valid_lsb_payload(secret_payload, password="CorrectPass")
        stego, _ = embed_file_adaptive(large_image.copy(), payload, "s.bin", "CorrectPass")
        with pytest.raises(ValueError):
            extract_file_adaptive(stego, password="WrongPass")

    def test_adaptive_no_password_raises(self, large_image, secret_payload):
        from adaptive_engine import embed_file_adaptive, extract_file_adaptive
        payload = make_valid_lsb_payload(secret_payload, password="APass")
        stego, _ = embed_file_adaptive(large_image.copy(), payload, "s.bin", "APass")
        with pytest.raises(ValueError, match="Password"):
            extract_file_adaptive(stego)

    def test_adaptive_lsb_difference_max_3_bits(self, large_image, secret_payload):
        """Adaptive encoding: no pixel channel may change by more than 7 (3 bits)."""
        from adaptive_engine import embed_file_adaptive
        payload = make_valid_lsb_payload(secret_payload, password="P")
        stego, _ = embed_file_adaptive(large_image.copy(), payload, "s.bin", "P")
        diff = np.abs(np.array(large_image).astype(int) - np.array(stego).astype(int))
        assert diff.max() <= 7, f"Adaptive: max pixel diff {diff.max()} exceeds 3-bit limit"
