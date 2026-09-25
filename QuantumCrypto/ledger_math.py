from blake3 import blake3

class MFHCEngine:
    """Manages Monotonic Feistel Hash-Chain ledger logic."""
    def __init__(self, node_key_hex: str):
        self.node_key = int(node_key_hex, 16)

    def generate_mask(self, y_prev_hex: str) -> bytes:
        y_prev_int = int(y_prev_hex, 16)
        xor_val = y_prev_int ^ self.node_key
        f_val = (pow(xor_val, 2) + xor_val + 1) % (2**256)
        return blake3(f_val.to_bytes(32, byteorder='big')).digest()

    def commit_block(self, y_prev_hex: str, sigma_u: bytes, m_receipt: str) -> str:
        y_prev_bytes = bytes.fromhex(y_prev_hex)
        M_chain = self.generate_mask(y_prev_hex)
        
        hasher = blake3()
        hasher.update(y_prev_bytes)
        hasher.update(M_chain)
        hasher.update(sigma_u)
        hasher.update(m_receipt.encode('utf-8'))
        
        return hasher.hexdigest()