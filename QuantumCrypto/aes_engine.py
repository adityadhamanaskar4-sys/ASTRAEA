from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class AESEngine:
    """Manages symmetric payload encryption, decryption, and key wrapping."""
    
    @staticmethod
    def encrypt_document(plaintext: bytes) -> tuple[bytes, bytes]:
        K_doc = get_random_bytes(32)
        nonce = get_random_bytes(12)  # FIPS standard 96-bit nonce for GCM
        
        cipher = AES.new(K_doc, AES.MODE_GCM, nonce=nonce)
        C_doc, tag = cipher.encrypt_and_digest(plaintext)
        
        # Package format: [12 bytes nonce] + [16 bytes tag] + [ciphertext]
        encrypted_payload = nonce + tag + C_doc
        return K_doc, encrypted_payload

    @staticmethod
    def decrypt_document(K_doc: bytes, encrypted_payload: bytes) -> bytes:
        nonce = encrypted_payload[:12]
        tag = encrypted_payload[12:28]
        C_doc = encrypted_payload[28:]
        
        cipher = AES.new(K_doc, AES.MODE_GCM, nonce=nonce)
        # Decrypt_and_verify inherently protects against tampering
        plaintext = cipher.decrypt_and_verify(C_doc, tag)
        return plaintext

    @staticmethod
    def wrap_key(K_shared: bytes, K_doc: bytes) -> bytes:
        cipher = AES.new(K_shared, AES.MODE_WRAP)
        W_u = cipher.encrypt(K_doc)
        return W_u

    @staticmethod
    def unwrap_key(K_shared: bytes, W_u: bytes) -> bytes:
        cipher = AES.new(K_shared, AES.MODE_WRAP)
        K_doc = cipher.decrypt(W_u)
        return K_doc