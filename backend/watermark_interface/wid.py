import logging
from blake3 import blake3
from QuantumCrypto.forensic_id import ForensicIDEngine
from QuantumCrypto.fec_engine import FECStegoEngine

logger = logging.getLogger("ASTRAEA.WatermarkID")


class WatermarkIDService:
    """
    Derives and protects the 256-bit Forensic Watermark ID (W_ID).
    W_ID = BLAKE3(sigma_u || y_i)
    Wraps payload with Reed-Solomon Forward Error Correction (FEC) for screen photo durability.
    """

    def __init__(self, ecc_symbols: int = 18):
        self.fec = FECStegoEngine(ecc_symbols=ecc_symbols)

    @staticmethod
    def derive_wid(sigma_u: bytes, y_i_hex: str) -> str:
        """Derives 64-character (256-bit) hex W_ID string from ML-DSA signature and ledger state y_i."""
        return ForensicIDEngine.derive_forensic_id(sigma_u, y_i_hex)

    def encode_wid_to_fec_bytes(self, wid_hex: str) -> bytes:
        """Encodes 64-character hex W_ID into Reed-Solomon protected bytes for DWT embedding."""
        return self.fec.encode_wid_for_dwt(wid_hex)

    def decode_fec_bytes_to_wid(self, fec_payload_bytes: bytes) -> str:
        """Decodes Reed-Solomon protected bytes extracted from DWT image back into hex W_ID."""
        return self.fec.decode_wid_from_dwt(fec_payload_bytes)
