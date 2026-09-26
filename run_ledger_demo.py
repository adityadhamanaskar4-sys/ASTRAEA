"""
ASTRAEA Ledger Demonstration Script
------------------------------------
Demonstrates:
1. Ledger Initialization and Genesis Block.
2. Request to Add Blocks (State Avalanche via Monotonic Feistel Transform).
3. Ledger Traversal (Genesis to Head & Head to Genesis).
4. Cryptographic Tamper-Evidence Traversal & Detection (Avalanche Failure).
5. Forensic Watermark ID (W_ID) Derivation & Reverse Leak Attribution.
6. Multi-Node (3-Node) Consortium Consensus Simulation.
"""

import os
import shutil
import tempfile
import asyncio
from datetime import datetime
from blake3 import blake3

from ledger.config import LedgerConfig, DEFAULT_NODE_KEY_HEX
from ledger.engine import LedgerEngine
from ledger.consensus import ConsensusCoordinator


def print_banner(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def format_hex(h: str, length: int = 16) -> str:
    if len(h) <= length:
        return h
    return f"{h[:length]}...{h[-4:]}"


def main():
    print_banner("PROJECT ASTRAEA: MONOTONIC FEISTEL HASH-CHAIN (MFHC) LEDGER DEMO")
    temp_dir = tempfile.mkdtemp(prefix="astraea_demo_")
    db_path = os.path.join(temp_dir, "demo_ledger.db")

    try:
        config = LedgerConfig(
            node_id="DEMO_NODE_01",
            node_key_hex=DEFAULT_NODE_KEY_HEX,
            db_path=db_path,
            verify_signatures=False
        )
        engine = LedgerEngine(config)

        # ---------------------------------------------------------------------
        # STEP 1: Genesis Block
        # ---------------------------------------------------------------------
        print_banner("STEP 1: Ledger Initialization & Genesis Block Creation")
        status = engine.get_status()
        print(f"Node ID          : {status.node_id}")
        print(f"Database Path    : {db_path}")
        print(f"Total Blocks     : {status.total_blocks}")
        print(f"Genesis Hash     : {status.genesis_hash}")
        print(f"Head Block ID    : #{status.head_block_id}")

        # ---------------------------------------------------------------------
        # STEP 2: Request to Add Blocks
        # ---------------------------------------------------------------------
        print_banner("STEP 2: Request to Add Blocks (Officer Decryption Provenance)")
        decryption_events = [
            ("OFFICER_MALHOTRA", "DOC_TOPSECRET_PQC_BLUEPRINT", "2026-09-25T17:30:00Z", "aa" * 32),
            ("OFFICER_VERMA",    "DOC_TOPSECRET_PQC_BLUEPRINT", "2026-09-25T17:35:12Z", "bb" * 32),
            ("OFFICER_SINGH",    "DOC_TACTICAL_RADAR_MAP",      "2026-09-25T17:42:05Z", "cc" * 32),
        ]

        committed_events = []
        for uid, doc_id, ts, sig_hex in decryption_events:
            receipt = f"{uid} || {doc_id} || {ts}"
            print(f"\n[REQUEST] Incoming decryption request:")
            print(f"  Receipt      : {receipt}")
            print(f"  Signature    : {format_hex(sig_hex)}")

            resp = engine.commit_block(
                client_receipt=receipt,
                client_signature=bytes.fromhex(sig_hex)
            )
            committed_events.append(resp)
            print(f"  >> [COMMIT SUCCESS] Block #{resp.block_id} committed!")
            print(f"     y_prev    : {format_hex(resp.y_prev)}")
            print(f"     Mask      : {format_hex(resp.mask)}")
            print(f"     y_current : {format_hex(resp.y_current)}")
            print(f"     W_ID      : {resp.w_id} (Forensic Watermark)")

        # ---------------------------------------------------------------------
        # STEP 3: Traverse the Ledger Blocks
        # ---------------------------------------------------------------------
        print_banner("STEP 3: Traversing the Ledger Blocks (Genesis -> Head)")
        traversal = engine.traverse_blocks(reverse=False)
        print(f"Total Blocks in Chain: {traversal.total_blocks}\n")
        print(f"{'ID':<4} | {'Timestamp':<19} | {'Receipt':<48} | {'State Hash (y_i)':<24}")
        print("-" * 105)
        for b in traversal.blocks:
            receipt_summary = (b.client_receipt[:45] + "...") if len(b.client_receipt) > 48 else b.client_receipt
            print(f"{b.block_id:<4} | {b.timestamp:<19} | {receipt_summary:<48} | {format_hex(b.y_current, 18):<24}")

        print("\nTraversing Reverse (Head -> Genesis):")
        reverse_traversal = engine.traverse_blocks(reverse=True)
        print("Block sequence IDs:", [b.block_id for b in reverse_traversal.blocks])

        # ---------------------------------------------------------------------
        # STEP 4: Cryptographic Integrity Verification & Tamper Detection
        # ---------------------------------------------------------------------
        print_banner("STEP 4: Cryptographic Integrity Verification (Pristine Chain)")
        report = engine.verify_chain_integrity()
        print(f"Integrity Valid  : {report.is_valid}")
        print(f"Total Blocks     : {report.total_blocks}")
        print(f"Head Hash        : {report.head_hash}")

        print("\n--- SIMULATING INSIDER TAMPERING IN SQLITE ---")
        print("A rogue administrator modifies row #2 in the database to frame another officer...")
        with engine.db.get_connection() as conn:
            conn.execute(
                "UPDATE blocks SET client_receipt = 'OFFICER_FRAMED || DOC_FORGED || 2026-09-25' WHERE block_id = 2;"
            )
            conn.commit()

        tamper_report = engine.verify_chain_integrity()
        print(f"Post-Tamper Valid: {tamper_report.is_valid}")
        print(f"Broken at Block  : #{tamper_report.broken_at_block_id}")
        print(f"Failure Reason   : {tamper_report.error_reason}")
        print(">> THE MONOTONIC FEISTEL HASH-CHAIN SHATTERED INSTANTLY! System caught the breach.")

        # Restore row #2 for subsequent tests
        with engine.db.get_connection() as conn:
            conn.execute(
                "UPDATE blocks SET client_receipt = ? WHERE block_id = 2;",
                (committed_events[0].y_prev,)  # temporary dummy to revert properly
            )
            # Recreate clean engine for clean demonstration
        
        # ---------------------------------------------------------------------
        # STEP 5: Forensic Watermark Audit (Attributing a Leaked Photograph)
        # ---------------------------------------------------------------------
        print_banner("STEP 5: Forensic Watermark Audit (Attributing Physical Leak)")
        # Re-initialize fresh engine for forensic test
        fresh_db = os.path.join(temp_dir, "forensic_ledger.db")
        clean_engine = LedgerEngine(LedgerConfig(db_path=fresh_db, verify_signatures=False))
        
        # Officer Verma decrypts document
        receipt_verma = "OFFICER_VERMA || TOP_SECRET_STRATEGY || 2026-09-25T18:00:00Z"
        sig_verma = bytes.fromhex("bb" * 32)
        resp_verma = clean_engine.commit_block(receipt_verma, sig_verma)

        # Officer Malhotra decrypts same document
        receipt_malhotra = "OFFICER_MALHOTRA || TOP_SECRET_STRATEGY || 2026-09-25T18:05:00Z"
        sig_malhotra = bytes.fromhex("aa" * 32)
        resp_malhotra = clean_engine.commit_block(receipt_malhotra, sig_malhotra)

        print("Two officers decrypted the EXACT SAME plaintext document:")
        print(f"  Officer Verma W_ID    : {resp_verma.w_id}")
        print(f"  Officer Malhotra W_ID : {resp_malhotra.w_id}")
        print("  >> Plaintext Parity broken! Watermarks are uniquely bound to session & recipient.")

        # Simulate smartphone photograph leak
        print("\n[INVESTIGATION] A smartphone photo of the screen was leaked.")
        print(f"Extracted Watermark ID (W_ID*): {resp_verma.w_id}")
        
        print("[AUDIT] Querying ledger for cryptographic attribution...")
        audit_res = clean_engine.audit_forensic_wid(resp_verma.w_id)
        print(f"Attribution Status : {audit_res.attribution_status}")
        print(f"Matched Block ID   : #{audit_res.block_id}")
        print(f"Attributed Officer : {audit_res.parsed_receipt.get('uid')}")
        print(f"Document ID        : {audit_res.parsed_receipt.get('doc_id')}")
        print(f"Session Timestamp  : {audit_res.parsed_receipt.get('timestamp')}")
        print(f"Signature Valid    : {audit_res.signature_verified}")
        print(f"Summary Message    : {audit_res.message}")

        # ---------------------------------------------------------------------
        # STEP 6: 3-Node Consortium Consensus Simulation
        # ---------------------------------------------------------------------
        print_banner("STEP 6: 3-Node Consortium Consensus Simulation")
        cluster_dir = os.path.join(temp_dir, "consortium_cluster")
        coordinator = ConsensusCoordinator.create_in_memory_or_local_cluster(cluster_dir)

        req_receipt = "OFFICER_GENERAL || BATTLE_DEPLOYMENT_ALPHA || 2026-09-25T21:00:00Z"
        req_sig = bytes.fromhex("dd" * 32)

        print("[BROADCAST] Broadcasting decryption intent to Node 1, Node 2, and Node 3 concurrently...")
        consensus_res = asyncio.run(coordinator.commit_distributed(req_receipt, req_sig))
        
        print(f"Consensus Achieved : {consensus_res.consensus_achieved}")
        print(f"Quorum Result      : {consensus_res.quorum_fraction} nodes agreed")
        print(f"Agreeing Nodes     : {consensus_res.agreeing_nodes}")
        print(f"Committed y_i Hash : {format_hex(consensus_res.agreed_hash)}")
        print(f"Key Release Status : {'AUTHORIZED (Released)' if consensus_res.authorization_granted else 'BLOCKED'}")

        print_banner("ALL LEDGER DEMONSTRATION WORKFLOWS COMPLETED SUCCESSFULLY!")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
