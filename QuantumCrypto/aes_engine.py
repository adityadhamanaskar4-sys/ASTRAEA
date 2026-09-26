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
        mode = getattr(AES, 'MODE_KW', None)
        if mode is not None:
            cipher = AES.new(K_shared, mode)
            if hasattr(cipher, 'seal'):
                return cipher.seal(K_doc)
            elif hasattr(cipher, 'encrypt'):
                return cipher.encrypt(K_doc)
        
        # Fallback to AES-GCM key wrapping
        nonce = get_random_bytes(12)
        cipher = AES.new(K_shared, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(K_doc)
        return nonce + tag + ciphertext

    @staticmethod
    def unwrap_key(K_shared: bytes, W_u: bytes) -> bytes:
        mode = getattr(AES, 'MODE_KW', None)
        if mode is not None and len(W_u) % 8 == 0:
            try:
                cipher = AES.new(K_shared, mode)
                if hasattr(cipher, 'unseal'):
                    return cipher.unseal(W_u)
                elif hasattr(cipher, 'decrypt'):
                    return cipher.decrypt(W_u)
            except Exception:
                pass
        
        # Fallback AES-GCM unwrapping
        nonce = W_u[:12]
        tag = W_u[12:28]
        ciphertext = W_u[28:]
        cipher = AES.new(K_shared, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)