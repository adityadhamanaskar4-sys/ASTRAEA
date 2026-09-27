import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

logger = logging.getLogger("ASTRAEA.SQLiteStore")

SAMPLE_USERS = [
    {
        "uid": "OFC-2291",
        "name": "Officer K. Rao",
        "role": "Lead Field Commander",
        "clearance_level": "TOP SECRET",
    },
    {
        "uid": "OFC-1187",
        "name": "Officer A. Verma",
        "role": "Signals Intelligence Analyst",
        "clearance_level": "CONFIDENTIAL",
    },
    {
        "uid": "OFC-3305",
        "name": "Officer S. Nair",
        "role": "Tactical Operations Officer",
        "clearance_level": "RESTRICTED",
    },
    {
        "uid": "OFC-4412",
        "name": "Major R. Menon",
        "role": "Air Defense Coordinator",
        "clearance_level": "TOP SECRET",
    },
    {
        "uid": "INV-9001",
        "name": "Inspector D. Sen",
        "role": "Cyber Forensics Investigator",
        "clearance_level": "SECRET",
    },
]


class SQLiteStore:
    """
    SQLite persistence layer for Project ASTRAEA users and document records.
    Stores data offline in airgapped SQLite databases alongside ledger blocks.
    """

    def __init__(self, db_path: str = "astraea_ledger.db"):
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    uid TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    clearance_level TEXT NOT NULL,
                    pk_kem TEXT,
                    sk_kem TEXT,
                    pk_dsa TEXT,
                    sk_dsa TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    body TEXT,
                    ciphertext_fp TEXT NOT NULL,
                    encrypted_payload BLOB NOT NULL,
                    k_doc BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    recipients_json TEXT NOT NULL,
                    lockboxes_json TEXT NOT NULL
                );
            """)
            conn.commit()

    def seed_sample_users(self, crypto_wrapper):
        """Populates sample users with generated ML-KEM and ML-DSA keys if table is empty."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS cnt FROM users;")
            if cursor.fetchone()["cnt"] > 0:
                return

            logger.info("Seeding sample military and intelligence officers into SQLite database...")
            for u in SAMPLE_USERS:
                pk_kem, sk_kem = crypto_wrapper.generate_kem_keypair()
                pk_dsa, sk_dsa = crypto_wrapper.generate_dsa_keypair()

                cursor.execute("""
                    INSERT INTO users (uid, name, role, clearance_level, pk_kem, sk_kem, pk_dsa, sk_dsa)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    u["uid"],
                    u["name"],
                    u["role"],
                    u["clearance_level"],
                    pk_kem.hex(),
                    sk_kem.hex(),
                    pk_dsa.hex(),
                    sk_dsa.hex()
                ))
            conn.commit()
            logger.info(f"Seeded {len(SAMPLE_USERS)} sample users into SQLite.")

    def get_all_users(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uid, name, role, clearance_level, pk_dsa, created_at FROM users ORDER BY uid;")
            rows = cursor.fetchall()
            return [
                {
                    "uid": r["uid"],
                    "name": r["name"],
                    "role": r["role"],
                    "clearance_level": r["clearance_level"],
                    "pk_dsa_hex": r["pk_dsa"],
                    "created_at": r["created_at"]
                }
                for r in rows
            ]

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT uid, name, role, clearance_level, pk_dsa, created_at FROM users WHERE uid = ?;", (uid,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "uid": row["uid"],
                "name": row["name"],
                "role": row["role"],
                "clearance_level": row["clearance_level"],
                "pk_dsa_hex": row["pk_dsa"],
                "created_at": row["created_at"]
            }

    def get_user_keys(self, uid: str) -> Optional[Dict[str, bytes]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT pk_kem, sk_kem, pk_dsa, sk_dsa FROM users WHERE uid = ?;", (uid,))
            row = cursor.fetchone()
            if not row or not row["pk_kem"]:
                return None
            return {
                "pk_kem": bytes.fromhex(row["pk_kem"]),
                "sk_kem": bytes.fromhex(row["sk_kem"]),
                "pk_dsa": bytes.fromhex(row["pk_dsa"]),
                "sk_dsa": bytes.fromhex(row["sk_dsa"]),
            }

    def save_user_keys(self, uid: str, name: str, role: str, clearance_level: str, keys: Dict[str, bytes]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (uid, name, role, clearance_level, pk_kem, sk_kem, pk_dsa, sk_dsa)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(uid) DO UPDATE SET
                    name=excluded.name,
                    role=excluded.role,
                    clearance_level=excluded.clearance_level,
                    pk_kem=excluded.pk_kem,
                    sk_kem=excluded.sk_kem,
                    pk_dsa=excluded.pk_dsa,
                    sk_dsa=excluded.sk_dsa;
            """, (
                uid,
                name,
                role,
                clearance_level,
                keys["pk_kem"].hex(),
                keys["sk_kem"].hex(),
                keys["pk_dsa"].hex(),
                keys["sk_dsa"].hex(),
            ))
            conn.commit()

    def save_document(self, doc_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO documents (
                    doc_id, title, classification, body, ciphertext_fp,
                    encrypted_payload, k_doc, created_at, recipients_json, lockboxes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                doc_data["doc_id"],
                doc_data["title"],
                doc_data["classification"],
                doc_data.get("plaintext_body", ""),
                doc_data["ciphertext_fp"],
                doc_data["encrypted_payload"],
                doc_data["K_doc"],
                doc_data["created_at"],
                json.dumps([r.model_dump() if hasattr(r, "model_dump") else r for r in doc_data["recipients"]]),
                json.dumps({
                    uid: {
                        "lockbox_ref": lb["lockbox_ref"],
                        "c_u": lb["c_u"].hex(),
                        "W_u": lb["W_u"].hex(),
                        "status": lb["status"]
                    }
                    for uid, lb in doc_data["lockboxes"].items()
                })
            ))
            conn.commit()

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE doc_id = ?;", (doc_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_doc_entry(row)

    def get_all_documents(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY created_at DESC;")
            rows = cursor.fetchall()
            return [self._row_to_doc_entry(r) for r in rows]

    def update_lockbox_status(self, doc_id: str, uid: str, status: str = "decrypted"):
        doc = self.get_document(doc_id)
        if not doc:
            return
        if uid in doc["lockboxes"]:
            doc["lockboxes"][uid]["status"] = status
        for r in doc["recipients"]:
            if (isinstance(r, dict) and r.get("uid") == uid) or (hasattr(r, "uid") and r.uid == uid):
                if isinstance(r, dict):
                    r["status"] = status
                else:
                    r.status = status
        self.save_document(doc)

    def _row_to_doc_entry(self, row: sqlite3.Row) -> Dict[str, Any]:
        from backend.models.responses import RecipientLockbox
        raw_recipients = json.loads(row["recipients_json"])
        recipients = [
            RecipientLockbox(**r) if isinstance(r, dict) else r
            for r in raw_recipients
        ]
        raw_lockboxes = json.loads(row["lockboxes_json"])
        lockboxes = {
            uid: {
                "lockbox_ref": lb["lockbox_ref"],
                "c_u": bytes.fromhex(lb["c_u"]),
                "W_u": bytes.fromhex(lb["W_u"]),
                "status": lb["status"]
            }
            for uid, lb in raw_lockboxes.items()
        }
        return {
            "doc_id": row["doc_id"],
            "title": row["title"],
            "classification": row["classification"],
            "plaintext_body": row["body"],
            "ciphertext_fp": row["ciphertext_fp"],
            "encrypted_payload": row["encrypted_payload"],
            "K_doc": row["k_doc"],
            "created_at": row["created_at"],
            "recipients": recipients,
            "lockboxes": lockboxes
        }
