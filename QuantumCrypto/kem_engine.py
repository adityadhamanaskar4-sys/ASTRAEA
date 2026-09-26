import oqs
import ctypes as ct

class KEMEngine:
    """Manages ML-KEM broadcast distribution keys (FIPS 203)."""
    ALGO = 'ML-KEM-768' 
    
    @classmethod
    def generate_keypair(cls) -> tuple[bytes, bytes]:
        with oqs.KeyEncapsulation(cls.ALGO) as kem:
            pk_KEM_u = kem.generate_keypair()
            sk_KEM_u = kem.export_secret_key()
            return pk_KEM_u, sk_KEM_u

    @classmethod
    def encapsulate_shared_secret(cls, pk_KEM_u: bytes) -> tuple[bytes, bytes]:
        with oqs.KeyEncapsulation(cls.ALGO) as kem:
            c_u, K_shared = kem.encap_secret(pk_KEM_u)
            return c_u, K_shared

    @classmethod
    def decapsulate_shared_secret(cls, sk_KEM_u: bytes, c_u: bytes) -> bytes:
        with oqs.KeyEncapsulation(cls.ALGO) as kem:
            # FIX: Cast Python bytes to C-types array to prevent memory-free errors
            kem.secret_key = (ct.c_uint8 * len(sk_KEM_u)).from_buffer_copy(sk_KEM_u)
            K_shared = kem.decap_secret(c_u)
            return K_shared