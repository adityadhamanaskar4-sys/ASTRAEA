import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from blake3 import blake3

GENESIS_Y_PREV = "0" * 64
GENESIS_MASK = "0" * 64
GENESIS_SIGNATURE = "GENESIS"
GENESIS_RECEIPT = "GENESIS"
GENESIS_Y_CURRENT = blake3(b"ASTRAEA_GENESIS_BLOCK").hexdigest()

from contextlib import contextmanager

class LedgerDatabase:
    """Manages append-only SQLite persistence for the Monotonic Feistel Hash-Chain."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Returns a configured SQLite connection with row factory and WAL mode, closing on exit."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Creates the blocks schema and inserts the Genesis Block if empty."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    block_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    y_prev TEXT NOT NULL,
                    mask TEXT NOT NULL,
                    client_signature TEXT NOT NULL,
                    client_receipt TEXT NOT NULL,
                    y_current TEXT NOT NULL
                );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_blocks_y_current ON blocks(y_current);")
            
            # Check if genesis block exists
            cursor.execute("SELECT COUNT(*) AS cnt FROM blocks;")
            count = cursor.fetchone()["cnt"]
            
            if count == 0:
                # Insert Genesis Block as defined in MFHC_Understand.md
                cursor.execute("""
                    INSERT INTO blocks (
                        timestamp, y_prev, mask, client_signature, client_receipt, y_current
                    ) VALUES (
                        CURRENT_TIMESTAMP, ?, ?, ?, ?, ?
                    );
                """, (
                    GENESIS_Y_PREV,
                    GENESIS_MASK,
                    GENESIS_SIGNATURE,
                    GENESIS_RECEIPT,
                    GENESIS_Y_CURRENT
                ))
                conn.commit()

    def insert_block(
        self,
        y_prev: str,
        mask: str,
        client_signature: str,
        client_receipt: str,
        y_current: str
    ) -> Dict[str, Any]:
        """Atomically appends a new verified block to the hash-chain."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO blocks (
                    timestamp, y_prev, mask, client_signature, client_receipt, y_current
                ) VALUES (
                    CURRENT_TIMESTAMP, ?, ?, ?, ?, ?
                );
            """, (y_prev, mask, client_signature, client_receipt, y_current))
            block_id = cursor.lastrowid
            conn.commit()

            cursor.execute("SELECT * FROM blocks WHERE block_id = ?;", (block_id,))
            row = cursor.fetchone()
            return dict(row)

    def get_head_block(self) -> Dict[str, Any]:
        """Retrieves the latest committed block in the ledger."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blocks ORDER BY block_id DESC LIMIT 1;")
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Ledger database is empty; Genesis block missing.")
            return dict(row)

    def get_genesis_block(self) -> Dict[str, Any]:
        """Retrieves the Genesis block (block_id = 1)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blocks ORDER BY block_id ASC LIMIT 1;")
            row = cursor.fetchone()
            if not row:
                raise RuntimeError("Ledger database is empty; Genesis block missing.")
            return dict(row)

    def get_block_by_id(self, block_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a block by its sequence index."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blocks WHERE block_id = ?;", (block_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_block_by_hash(self, y_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves a block by its state hash y_current."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blocks WHERE y_current = ?;", (y_hash,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_blocks_paginated(
        self,
        offset: int = 0,
        limit: Optional[int] = None,
        reverse: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Traverse blocks in the ledger.
        If reverse is False: Genesis -> Head (ASC)
        If reverse is True: Head -> Genesis (DESC)
        """
        order_clause = "DESC" if reverse else "ASC"
        query = f"SELECT * FROM blocks ORDER BY block_id {order_clause}"
        params: List[Any] = []

        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset > 0:
            query += " LIMIT -1 OFFSET ?"
            params.append(offset)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def count_blocks(self) -> int:
        """Returns the total number of blocks in the ledger."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS cnt FROM blocks;")
            return cursor.fetchone()["cnt"]

    def get_all_blocks_for_audit(self) -> List[Dict[str, Any]]:
        """Retrieves all non-genesis blocks for reverse forensic watermark lookup."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM blocks WHERE block_id > 1 ORDER BY block_id ASC;")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
