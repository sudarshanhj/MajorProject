import numpy as np
from PIL import Image
from typing import Tuple

# DEEPSTEGAI_V1 Standard Signature
MAGIC = b"DEEPSTEGAI_V1"

# The header layout for extraction logic:
# 13 bytes (MAGIC) + 1 byte (Proto) + 1 byte (Enc) + 2 bytes (Count) + 4 bytes (PayloadLen) + 2 bytes (FnameLen)
# = 13 + 10 = 23 bytes total
HEADER_LEN = 13 + 10 

def bytes_to_bits(b: bytes) -> np.ndarray:
    """
    Converts a byte string into a numpy array of bits (0s and 1s).
    Example: b'A' (65) -> [0 1 0 0 0 0 0 1]
    """
    return np.unpackbits(np.frombuffer(b, dtype=np.uint8))

def bits_to_bytes(bits: np.ndarray, nbytes: int = None) -> bytes:
    """
    Reconstructs bytes from a stream of bits.
    We pad with zeros if the bit count isn't a multiple of 8.
    """
    if bits.size % 8 != 0:
        pad = 8 - (bits.size % 8)
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    out = np.packbits(bits).tobytes()
    return out if nbytes is None else out[:nbytes]

def image_capacity_bits(img: Image.Image) -> int:
    """
    Calculates how much data we can hide in the image.
    Since we hide 1 bit per color channel (R, G, B) of every pixel:
    Capacity = Width * Height * 3 bits.
    """
    w, h = img.size
    return 3 * w * h

def embed_payload_into_image(cover_img: Image.Image, payload_bytes: bytes) -> Image.Image:
    """
    The core logic for hiding data.
    """
    arr = np.array(cover_img.convert("RGB"))
    flat = arr.flatten()
    bits = bytes_to_bits(payload_bytes).astype(np.uint8)
    
    if len(bits) > len(flat):
        raise ValueError(f"Data is too large for this image. Try a larger image or smaller file.")
    
    mask = np.uint8(0xFE)
    flat_head = flat[:len(bits)]
    flat[:len(bits)] = (flat_head & mask) | bits
    out = flat.reshape(arr.shape)
    return Image.fromarray(out)


def extract_payload_from_image(stego_img: Image.Image) -> Tuple[int, bytes, bytes]:
    """
    Recovers the hidden data from an image.
    Returns: (mode_id, payload_bytes, signature_bytes)
    """
    arr = np.array(stego_img.convert("RGB"))
    flat = arr.flatten()
    
    # First, let's extract the header bits
    need_bits = HEADER_LEN * 8
    header_bits = (flat[:need_bits] & 1).astype(np.uint8)
    header_bytes = bits_to_bytes(header_bits)
    
    # Check if our signature is present
    if len(header_bytes) < HEADER_LEN or not header_bytes.startswith(MAGIC):
        raise ValueError("This image doesn't contain a valid DeepStegAI header.")
    
    # Parse the header
    # struct.pack(">BBHIH", proto_id, is_encrypted, file_count, len(final_payload), len(fname_bytes))
    # Indices: 13 (Proto), 14 (Enc), 15 (Count), 17 (PayloadLen), 21 (FnameLen)
    # But wait, it's easier to use the fixed offset or just extract the payload_len from the correct offset:
    # MAGIC (13) + Proto (1) + Enc (1) + Count (2) = 17 bytes offset to PayloadLen
    payload_len = int.from_bytes(header_bytes[17:21], "big")
    fname_len = int.from_bytes(header_bytes[21:23], "big")
    
    # Calculate total bits needed including the payload AND checksum AND filename
    # Structure: MAGIC + METADATA_FIXED + FILENAME + PAYLOAD + CHECKSUM(32)
    total_len = HEADER_LEN + fname_len + payload_len + 32
    total_bits = total_len * 8
    
    if total_bits > len(flat):
        raise ValueError("Header says payload is larger than the image itself. File might be corrupted.")
    
    # Extract the full payload bits
    payload_bits = (flat[:total_bits] & 1).astype(np.uint8)
    
    # Convert back to bytes
    payload_bytes = bits_to_bytes(payload_bits)
    
    # We return the whole block for protocol.py to handle
    return 0, payload_bytes, None
