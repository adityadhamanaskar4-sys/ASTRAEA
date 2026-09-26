import reedsolo

class FECStegoEngine:
    """Wraps the 256-bit W_ID in Reed-Solomon Forward Error Correction (FEC)."""
    
    def __init__(self, ecc_symbols: int = 18):
        self.rs = reedsolo.RSCodec(ecc_symbols)

    def encode_wid_for_dwt(self, wid_hex: str) -> bytes:
        if len(wid_hex) != 64:
            raise ValueError("W_ID must be exactly 256 bits (64 hex characters).")
            
        wid_bytes = bytes.fromhex(wid_hex)
        protected_payload = self.rs.encode(wid_bytes)
        return protected_payload

    def decode_wid_from_dwt(self, extracted_bytes: bytes) -> str:
        try:
            healed_bytes, _, _ = self.rs.decode(extracted_bytes)
            recovered_wid_hex = healed_bytes.hex()
            return recovered_wid_hex
        except reedsolo.ReedSolomonError:
            raise ValueError("Analog distortion exceeded FEC threshold. W_ID unrecoverable.")