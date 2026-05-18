import numpy as np
from PIL import Image
from stego_engine import bits_to_bytes, MAGIC

def scan_image_for_signature(img: Image.Image) -> dict:
    """
    Analyzes an image to see if it contains our specific digital signature.
    
    How it works:
    1. We look at the very first 32 pixels (roughly).
    2. We extract the Least Significant Bit from each.
    3. We combine these bits to form 4 bytes.
    4. We check if these 4 bytes match our magic signature "DSAI".
    
    This is extremely fast because we don't need to process the whole image,
    just the header at the beginning.
    """
    try:
        # Convert to RGB to ensure consistent channel count
        arr = np.array(img.convert("RGB"))
        flat = arr.flatten()
        
        # Safety check: is the image big enough to even have a header?
        if len(flat) < 104:
            return {"detected": False, "error": "Image is too small to contain data."}
            
        # Extract the first 104 bits (13 bytes * 8 bits) for V1
        header_bits = (flat[:104] & 1).astype(np.uint8)
        header_bytes = bits_to_bytes(header_bits)
        
        # Compare with our known signatures
        if header_bytes.startswith(MAGIC):
            # For V1, the 14th byte (index 13) is the proto_id (0 for LSB, 1 for Adaptive)
            # But we might only have extracted 104 bits. 
            # I'll check a bit more if possible, but for now just use the signature.
            
            # Re-read 120 bits to get the proto byte too
            full_header_bits = (flat[:120] & 1).astype(np.uint8)
            full_header_bytes = bits_to_bytes(full_header_bits)
            proto_id = full_header_bytes[13] if len(full_header_bytes) > 13 else 0
            
            method_name = "Standard LSB" if proto_id == 0 else "Adaptive Edge"
            
            return {
                "detected": True,
                "confidence": "100%",
                "message": f"DeepStegAI Signature Found ({method_name})",
                "magic_bytes": header_bytes.hex()
            }
        else:
            return {
                "detected": False,
                "confidence": "0%",
                "message": "No Signature Found",
                "magic_bytes": header_bytes.hex()
            }
            
    except Exception as e:
        return {"detected": False, "error": str(e)}
