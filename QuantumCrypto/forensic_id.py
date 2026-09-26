from blake3 import blake3

class ForensicIDEngine:
    """Derives the deterministic steganographic watermark ID."""
    @staticmethod
    def derive_forensic_id(sigma_u: bytes, y_i_hex: str) -> str:
        hasher = blake3()
        hasher.update(sigma_u)
        hasher.update(bytes.fromhex(y_i_hex))
        
        # Returns 64-character hex string representing the exact 256-bit W_ID
        return hasher.hexdigest()