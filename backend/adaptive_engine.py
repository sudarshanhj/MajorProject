import cv2
import numpy as np
from PIL import Image
import os
import random
from crypto_utils import aes_encrypt, aes_decrypt, derive_key

# --- Constants ---
# DEEPSTEGAI_V1 Standard Signature
MAGIC_V1 = b"DEEPSTEGAI_V1"
# Header: Proto(1) + Enc(1) + Count(2) + PLen(4) + FLen(2) = 10 bytes
HEADER_LEN = 10

def get_stable_edge_map(img_pil: Image.Image) -> np.ndarray:
    """
    Generates a STABLE edge map that won't change after embedding.
    Uses Green Channel MSBs for stability.
    """
    img_arr = np.array(img_pil.convert("RGB"))
    gray_stable = img_arr[:, :, 1] & 0xF0
    edges = cv2.Canny(gray_stable, 100, 200)
    return edges

def embed_file_adaptive(cover_img: Image.Image, file_bytes: bytes, filename: str, password: str, signature: bytes = None) -> tuple[Image.Image, str]:
    """
    Embeds a file using HYBRID Adaptive Edge Steganography.
    Ultra-optimized version.
    """
    arr = np.array(cover_img.convert("RGB")).astype(np.uint8)
    h, w, _ = arr.shape
    
    # 1. Embed Magic Bits (Fast 1D view) - We use V1!
    flat_view = arr.ravel()
    magic_bits = np.unpackbits(np.frombuffer(MAGIC_V1, dtype=np.uint8))
    # Signature is 13 bytes = 104 bits. We use first 104 pixel-channels.
    flat_view[:104] = (flat_view[:104] & 0xFE) | magic_bits
    
    # 2. Get Edge Map and Shuffled Indices
    edges_flat = get_stable_edge_map(cover_img).ravel()
    # Payload indices start after magic bits. 35 pixels * 3 channels = 105. 
    # We use 35 to be safe and simple.
    valid_indices = np.arange(35, h * w)
    
    # 3. Prepare Shuffle/Recovery Token
    from crypto_utils import derive_key
    recovery_token = derive_key(password).decode('utf-8')
    
    # Standard V1 Protocol: The payload passed ALREADY contains Signature + Metadata + Data
    bits = np.unpackbits(np.frombuffer(file_bytes, dtype=np.uint8))
    total_bits = len(bits)
    
    # 4. Shuffle Indices using recovery_token
    import hashlib
    seed_val = int(hashlib.md5(recovery_token.encode('utf-8')).hexdigest(), 16) % (2**32 - 1)
    rng = np.random.default_rng(seed_val)
    rng.shuffle(valid_indices)
    
    # 5. Smart Slicing: How many pixels do we actually need?
    # Each pixel provides (3 channels * bits_per_channel)
    # bits_per_pixel is 9 if edge (3*3), 3 if smooth (3*1)
    bpp_map = np.where(edges_flat[valid_indices] == 255, 9, 3)
    cum_capacity = np.cumsum(bpp_map)
    needed_pixels_count = np.searchsorted(cum_capacity, total_bits) + 1
    
    if needed_pixels_count > len(valid_indices):
        raise ValueError("Payload is too large for this cover image with the given password.")
        
    target_indices = valid_indices[:needed_pixels_count]
    flat_pixels = arr.reshape(-1, 3)
    
    # 6. --- ULTRA OPTIMIZED VECTORIZATION ---
    bpc_arr = np.where(edges_flat[target_indices] == 255, 3, 1)
    bpc_arr_expanded = np.repeat(bpc_arr[:, None], 3, axis=1)
    bpc_flat = bpc_arr_expanded.ravel()
    
    total_capacity = np.sum(bpc_flat)
    if len(bits) < total_capacity:
        bits = np.pad(bits, (0, total_capacity - len(bits)), 'constant', constant_values=0)
        
    bits_matrix = np.zeros((len(bpc_flat), 3), dtype=np.uint8)
    mask = np.zeros((len(bpc_flat), 3), dtype=bool)
    mask[bpc_flat == 3] = [True, True, True]
    mask[bpc_flat == 1] = [False, False, True]
    
    bits_matrix[mask] = bits
    
    new_vals_flat = (bits_matrix[:, 0] << 2) | (bits_matrix[:, 1] << 1) | bits_matrix[:, 2]
    new_vals = new_vals_flat.reshape(-1, 3)
    
    payload_pixels = flat_pixels[target_indices]
    clear_mask = ~((1 << bpc_arr_expanded) - 1) & 0xFF
    
    flat_pixels[target_indices] = (payload_pixels & clear_mask) | (new_vals & 0xFF)
            
    return Image.fromarray(arr), recovery_token

def extract_file_adaptive(stego_img: Image.Image, password: str = '', recovery_token: str = '') -> tuple[str, bytes, bytes]:
    """
    Extracts a file using HYBRID Adaptive Edge Steganography.
    High-Speed Two-Pass Extraction.
    """
    if not password and not recovery_token:
        raise ValueError("Password/Recovery Token required")

    f_key_str = recovery_token if recovery_token else derive_key(password).decode('utf-8')
    arr = np.array(stego_img.convert("RGB")).astype(np.uint8)
    h, w, _ = arr.shape
    flat_pixels = arr.reshape(-1, 3)
    
    # 1. Magic Check
    flat_view = arr.ravel()
    # Extract 104 bits for V1 signature
    magic_bytes = np.packbits(flat_view[:104] & 1).tobytes()
    
    if not magic_bytes.startswith(MAGIC_V1):
        raise ValueError("Incorrect password. No valid steganography data found with the provided password.")
        
    # 2. Shuffle Setup
    edges_flat = get_stable_edge_map(stego_img).ravel()
    valid_indices = np.arange(35, h * w)
    
    if True:  # We always use the new fast RNG since password creates a token
        import hashlib
        seed_val = int(hashlib.md5(f_key_str.encode('utf-8')).hexdigest(), 16) % (2**32 - 1)
        rng = np.random.default_rng(seed_val)
        rng.shuffle(valid_indices)
    
    # 3. Pass 1: Extract Header Only
    # Header is 10 bytes = 80 bits. 64 pixels is enough.
    header_indices = valid_indices[:64]
    header_bits = []
    for idx in header_indices:
        bpc = 3 if edges_flat[idx] == 255 else 1
        for ch in range(3):
            val = int(flat_pixels[idx, ch]) & ((1 << bpc) - 1)
            for i in range(bpc - 1, -1, -1):
                header_bits.append((val >> i) & 1)
                
    h_bytes = np.packbits(np.array(header_bits[:256], dtype=np.uint8)).tobytes()
    # MAGIC_V1 is 13 bytes. Metadata starts right after.
    # Structure: Proto(1), Enc(1), Count(2), PLen(4), FLen(2) -> PLen is at 13 + 4 = 17.
    p_len = int.from_bytes(h_bytes[17:21], 'big')
    f_len = int.from_bytes(h_bytes[21:23], 'big')
    
    if f_len > 1000 or p_len > 50*1024*1024:
        raise ValueError("Incorrect password. Please verify and try again.")
        
    # 4. Pass 2: Extract exactly what we need
    # Structure for full byte block: MAGIC(13) + MetadataFix(10) + Fname(FLen) + Payload(PLen) + Checksum(32)
    total_len = 13 + 10 + f_len + p_len + 32
    total_bits_needed = total_len * 8
    
    # Re-calculate how many pixels needed
    bpp_map = np.where(edges_flat[valid_indices] == 255, 9, 3)
    cum_cap = np.cumsum(bpp_map)
    needed_count = np.searchsorted(cum_cap, total_bits_needed) + 1
    
    payload_indices = valid_indices[:needed_count]
    # --- ULTRA OPTIMIZED VECTORIZATION ---
    bpc_arr = np.where(edges_flat[payload_indices] == 255, 3, 1)
    bpc_arr_expanded = np.repeat(bpc_arr[:, None], 3, axis=1)
    bpc_flat = bpc_arr_expanded.ravel()
    
    payload_pixels = flat_pixels[payload_indices]
    vals = payload_pixels & ((1 << bpc_arr_expanded) - 1)
    vals_flat = vals.ravel()
    
    bits_2 = (vals_flat >> 2) & 1
    bits_1 = (vals_flat >> 1) & 1
    bits_0 = (vals_flat >> 0) & 1
    all_bits_matrix = np.column_stack([bits_2, bits_1, bits_0])
    
    mask = np.zeros((len(vals_flat), 3), dtype=bool)
    mask[bpc_flat == 3] = [True, True, True]
    mask[bpc_flat == 1] = [False, False, True]
    
    all_extracted_bits = all_bits_matrix[mask]
                
    # 5. Final Parse
    all_extracted_bits = all_extracted_bits[:total_bits_needed]
    data_bytes = np.packbits(np.array(all_extracted_bits, dtype=np.uint8)).tobytes()
    
    # data_bytes already contains the V1 protocol block perfectly
    return "", data_bytes, None
