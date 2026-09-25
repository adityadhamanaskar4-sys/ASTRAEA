import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# Default 256-bit Node Key (32 bytes hex) used for local prototype
DEFAULT_NODE_KEY_HEX = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

@dataclass
class LedgerConfig:
    """Configuration for an individual ASTRAEA DLT Ledger Node."""
    node_id: str = "node_1"
    node_key_hex: str = DEFAULT_NODE_KEY_HEX
    db_path: str = "data/ledger.db"
    peer_urls: List[str] = field(default_factory=lambda: [
        "http://127.0.0.1:8001",
        "http://127.0.0.1:8002",
        "http://127.0.0.1:8003"
    ])
    verify_signatures: bool = True
    consensus_quorum: int = 2  # Strict 2-of-3 majority

    @classmethod
    def from_env(cls, prefix: str = "ASTRAEA_") -> "LedgerConfig":
        """Load configuration from environment variables with fallbacks."""
        node_id = os.getenv(f"{prefix}NODE_ID", "node_1")
        node_key_hex = os.getenv(f"{prefix}NODE_KEY", DEFAULT_NODE_KEY_HEX)
        db_path = os.getenv(f"{prefix}DB_PATH", f"data/ledger_{node_id}.db")
        peers_str = os.getenv(f"{prefix}PEERS", "")
        
        if peers_str:
            peer_urls = [p.strip() for p in peers_str.split(",") if p.strip()]
        else:
            peer_urls = [
                "http://127.0.0.1:8001",
                "http://127.0.0.1:8002",
                "http://127.0.0.1:8003"
            ]

        verify_sig = os.getenv(f"{prefix}VERIFY_SIGNATURES", "true").lower() in ("1", "true", "yes")

        return cls(
            node_id=node_id,
            node_key_hex=node_key_hex,
            db_path=db_path,
            peer_urls=peer_urls,
            verify_signatures=verify_sig
        )

    def ensure_db_dir(self) -> Path:
        """Ensure the parent directory for the SQLite database exists."""
        db_file = Path(self.db_path).resolve()
        db_file.parent.mkdir(parents=True, exist_ok=True)
        return db_file
