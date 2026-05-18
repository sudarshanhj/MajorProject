import hashlib
import struct
import io
import zipfile
from crypto_utils import aes_encrypt, aes_decrypt

SIGNATURE = b"DEEPSTEGAI_V1"

# Metadata Layout (Approximate plan):
# Signature (13 bytes)
# Protocol (1 byte: 0=LSB, 1=Adaptive)
# Encryption Flag (1 byte: 0=No, 1=Yes)
# File Count (2 bytes)
# Payload Length (4 bytes)
# Filename Length (2 bytes)
# Filename (Variable)
# Checksum (32 bytes - SHA256 of metadata + encrypted payload)

def calculate_checksum(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def package_payload(files: list, protocol: str, password: str = None, recovery_token: str = None) -> bytes:
    """
    Implements the standardized DEEPSTEGAI_V1 protocol.
    Order: signature → metadata → encrypted payload → checksum
    """
    # 1. Multi-file handling: ZIP if needed
    if len(files) > 1 or (len(files) == 1 and files[0]['name'].endswith('.zip')):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                zf.writestr(f['name'], f['data'])
        payload_data = zip_buffer.getvalue()
        main_filename = "bundle.zip"
        file_count = len(files)
    else:
        payload_data = files[0]['data']
        main_filename = files[0]['name']
        file_count = 1

    # 2. Encryption Workflow
    is_encrypted = 1 if password else 0
    final_payload = payload_data
    if is_encrypted:
        # We use the existing aes_encrypt which handles Fernet
        encrypted_data, _ = aes_encrypt(payload_data, password)
        final_payload = encrypted_data

    # 3. Metadata Structure
    proto_id = 0 if protocol.upper() == 'LSB' else 1
    fname_bytes = main_filename.encode('utf-8')
    
    # Pack metadata: Proto(B), Enc(B), Count(H), PayloadLen(I), FnameLen(H)
    metadata_fixed = struct.pack(">BBHIH", proto_id, is_encrypted, file_count, len(final_payload), len(fname_bytes))
    metadata_block = metadata_fixed + fname_bytes
    
    # 4. Assembly: signature + metadata + encrypted payload
    full_block_so_far = SIGNATURE + metadata_block + final_payload
    
    # 5. Checksum
    checksum = calculate_checksum(full_block_so_far)
    
    return full_block_so_far + checksum

def unpackage_payload(raw_data: bytes, password: str = None, recovery_token: str = None):
    """
    Reverses the DEEPSTEGAI_V1 protocol.
    """
    if not raw_data.startswith(SIGNATURE):
        raise ValueError("Extraction Error: No Signature Detected")
    
    cursor = len(SIGNATURE)
    
    # Parse metadata fixed part
    fixed_size = struct.calcsize(">BBHIH")
    if len(raw_data) < cursor + fixed_size:
        raise ValueError("Extraction Error: Corrupted Metadata")
        
    proto_id, is_encrypted, file_count, payload_len, fname_len = struct.unpack(">BBHIH", raw_data[cursor:cursor+fixed_size])
    cursor += fixed_size
    
    # Parse filename
    if len(raw_data) < cursor + fname_len:
        raise ValueError("Extraction Error: Invalid Filename Metadata")
    filename = raw_data[cursor:cursor+fname_len].decode('utf-8')
    cursor += fname_len
    
    # Parse payload
    if len(raw_data) < cursor + payload_len + 32: # 32 is checksum
        raise ValueError("Extraction Error: Payload Length Mismatch")
    encrypted_payload = raw_data[cursor:cursor+payload_len]
    cursor += payload_len
    
    # Parse and Verify Checksum
    provided_checksum = raw_data[cursor:cursor+32]
    expected_checksum = calculate_checksum(raw_data[:cursor])
    if provided_checksum != expected_checksum:
        # Most common cause: wrong password → wrong pixel shuffle → garbage block extracted.
        # Surface a simple, actionable message instead of a technical internal error.
        raise ValueError("Incorrect password. The data could not be extracted with the provided credentials.")
    
    # 6. Decryption Workflow
    decrypted_data = encrypted_payload
    if is_encrypted:
        if not password and not recovery_token:
            raise ValueError("Password or recovery token is required to decrypt this file.")
        
        try:
            # Try decrypting with password first, then token if provided
            if recovery_token:
                decrypted_data = aes_decrypt(encrypted_payload, recovery_token, is_token=True)
            else:
                decrypted_data = aes_decrypt(encrypted_payload, password, is_token=False)
        except Exception:
            raise ValueError("Incorrect password. Please check your password and try again.")

    # 7. Post-processing: Unzip if bundle
    if file_count > 1 or filename == "bundle.zip":
        try:
            zip_buffer = io.BytesIO(decrypted_data)
            with zipfile.ZipFile(zip_buffer, "r") as zf:
                # We return the list of files if it was a bundle
                extracted_files = []
                for name in zf.namelist():
                    extracted_files.append({'name': name, 'data': zf.read(name)})
                return extracted_files, True # True means it's a bundle
        except:
             # If it wasn't actually a zip, just return the data
             return [{'name': filename, 'data': decrypted_data}], False
             
    return [{'name': filename, 'data': decrypted_data}], False
