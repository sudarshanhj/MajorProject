import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Check if the cryptography library is installed.
# We use this flag to handle cases where the user might not have the library,
# falling back to a simple XOR method if needed (though AES is highly recommended).
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from base64 import urlsafe_b64encode
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False

def derive_key(key_input: str) -> bytes:
    """
    Generates a secure encryption key from the user's password.
    """
    password = key_input.encode()
    salt = b'deepsteg_ai_key_salt' 
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    
    return urlsafe_b64encode(kdf.derive(password))

def xor_encrypt_decrypt(data: bytes, key: str) -> bytes:
    """
    A simple fallback method if the main encryption library isn't available.
    It just flips bits using the key. Not very secure, but better than nothing.
    """
    key_bytes = key.encode('utf-8')
    key_len = len(key_bytes)
    # Cycle through the key and XOR each byte of data
    return bytes(data[i] ^ key_bytes[i % key_len] for i in range(len(data)))

def aes_encrypt(data: bytes, key_input: str) -> tuple[bytes, str]:
    """
    Encrypts the data using AES. Returns (encrypted_bytes, recovery_token).
    """
    if HAVE_CRYPTO:
        f_key = derive_key(key_input)
        fernet = Fernet(f_key)
        encrypted_data = fernet.encrypt(data)
        # Return data AND the key (as a string token)
        return encrypted_data, f_key.decode('utf-8')
    else:
        return xor_encrypt_decrypt(data, key_input), "NO_CRYPTO"

def aes_decrypt(data: bytes, key_input: str, is_token: bool = False) -> bytes:
    """
    Decrypts data. 
    If is_token=True, key_input is the raw base64 key.
    If is_token=False, key_input is the password.
    """
    if HAVE_CRYPTO:
        try:
            if is_token:
                f_key = key_input.encode('utf-8')
            else:
                f_key = derive_key(key_input)
                
            fernet = Fernet(f_key)
            return fernet.decrypt(data)
        except Exception:
            raise ValueError("Incorrect Password")
    else:
        return xor_encrypt_decrypt(data, key_input)

# --- Digital Signatures (ECDSA) ---
try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import utils
except ImportError:
    pass

def generate_key_pair() -> tuple[bytes, bytes]:
    """
    Generates a new ECDSA key pair (Private, Public).
    Returns PEM encoded bytes.
    """
    if not HAVE_CRYPTO:
        return b"NO_CRYPTO", b"NO_CRYPTO"
        
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return pem_private, pem_public

def sign_data(data: bytes, pem_private_key: str) -> bytes:
    """
    Signs data using the private key. Returns signature bytes.
    """
    if not HAVE_CRYPTO: return b""
    
    try:
        # Load key
        if isinstance(pem_private_key, str):
            pem_bytes = pem_private_key.encode()
        else:
            pem_bytes = pem_private_key
            
        private_key = serialization.load_pem_private_key(
            pem_bytes,
            password=None
        )
        
        signature = private_key.sign(
            data,
            ec.ECDSA(hashes.SHA256())
        )
        return signature
    except Exception as e:
        raise ValueError(f"Signing Failed: {e}")

def verify_signature(data: bytes, signature: bytes, pem_public_key: str) -> bool:
    """
    Verifies the signature of the data using the public key.
    """
    if not HAVE_CRYPTO: return False
    
    try:
        if isinstance(pem_public_key, str):
            pem_bytes = pem_public_key.encode()
        else:
            pem_bytes = pem_public_key
            
        public_key = serialization.load_pem_public_key(pem_bytes)
        
        public_key.verify(
            signature,
            data,
            ec.ECDSA(hashes.SHA256())
        )
        return True # Verified
    except Exception:
        return False # Invalid
