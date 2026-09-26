import oqs
import ctypes as ct

class DSAEngine:
    """Manages ML-DSA signatures for decryption receipts (FIPS 204)."""
    ALGO = 'ML-DSA-65'
    
    @classmethod
    def generate_keypair(cls) -> tuple[bytes, bytes]:
        with oqs.Signature(cls.ALGO) as sig:
            pk_DSA_u = sig.generate_keypair()
            sk_DSA_u = sig.export_secret_key()
            return pk_DSA_u, sk_DSA_u

    @classmethod
    def sign_receipt(cls, sk_DSA_u: bytes, m_receipt: str) -> bytes:
        with oqs.Signature(cls.ALGO) as sig:
            # FIX: Cast Python bytes to C-types array to prevent memory-free errors
            sig.secret_key = (ct.c_uint8 * len(sk_DSA_u)).from_buffer_copy(sk_DSA_u)
            sigma_u = sig.sign(m_receipt.encode('utf-8'))
            return sigma_u

    @classmethod
    def verify_receipt(cls, pk_DSA_u: bytes, m_receipt: str, sigma_u: bytes) -> bool:
        with oqs.Signature(cls.ALGO) as sig:
            try:
                return sig.verify(m_receipt.encode('utf-8'), sigma_u, pk_DSA_u)
            except Exception:
                return False