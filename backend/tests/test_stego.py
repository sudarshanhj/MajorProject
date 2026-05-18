import pytest
import numpy as np
from PIL import Image
import io
import sys
import os

# Ensure backend root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego_engine import (
    bytes_to_bits, bits_to_bytes, image_capacity_bits, 
    embed_payload_into_image, extract_payload_from_image, MAGIC
)

@pytest.fixture
def dummy_image():
    # 100x100 Red square
    img = Image.new('RGB', (100, 100), color = 'red')
    return img

def test_bits_bytes_conversion():
    data = b"Hello, Stego!"
    bits = bytes_to_bits(data)
    recovered_data = bits_to_bytes(bits, len(data))
    assert data == recovered_data
    
def test_image_capacity(dummy_image):
    # 100 * 100 * 3 = 30000 bits
    assert image_capacity_bits(dummy_image) == 30000

def test_embed_and_extract_payload(dummy_image):
    """
    Round-trip test using the canonical DEEPSTEGAI_V1 protocol.
    Uses a larger image (500x500) so capacity is sufficient.
    """
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from protocol import package_payload, unpackage_payload
    from PIL import Image as PILImage

    # Use a bigger image because 100x100 is too small for the full DEEPSTEGAI_V1 block
    cover = PILImage.new("RGB", (500, 500), color="blue")
    secret = b"Top Secret Payload 12345"

    # Build a proper V1 protocol block
    full_payload = package_payload([{"name": "secret.txt", "data": secret}], "LSB")

    stego_img = embed_payload_into_image(cover, full_payload)

    # Extract the full V1 block
    mode_id, raw_block, signature = extract_payload_from_image(stego_img)
    assert mode_id == 0
    assert signature is None

    # Unpackage using the canonical protocol  
    results, is_bundle = unpackage_payload(raw_block)
    assert not is_bundle
    assert results[0]["data"] == secret

def test_embed_too_large_payload(dummy_image):
    # Capacity is 30000 bits = 3750 bytes
    large_payload = b"A" * 4000
    with pytest.raises(ValueError, match="Data is too large for this image"):
        embed_payload_into_image(dummy_image, large_payload)

def test_extract_invalid_header(dummy_image):
    """A plain unmodified image has no DSAI magic bytes — must raise ValueError."""
    with pytest.raises(ValueError, match="valid DeepStegAI header"):
        extract_payload_from_image(dummy_image)
