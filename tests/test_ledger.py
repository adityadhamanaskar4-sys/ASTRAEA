import os
import shutil
import tempfile
import unittest
from blake3 import blake3
from fastapi.testclient import TestClient

from ledger.config import LedgerConfig, DEFAULT_NODE_KEY_HEX
from ledger.db import (
    LedgerDatabase,
    GENESIS_Y_PREV,
    GENESIS_MASK,
    GENESIS_SIGNATURE,
    GENESIS_RECEIPT,
    GENESIS_Y_CURRENT
)
from ledger.engine import LedgerEngine
from ledger.consensus import ConsensusCoordinator
from ledger.api import create_ledger_app
from QuantumCrypto.ledger_math import MFHCEngine
from QuantumCrypto.forensic_id import ForensicIDEngine


class TestASTRAEALedger(unittest.TestCase):
    def setUp(self):
        # Create a fresh temporary directory for each test
        self.test_dir = tempfile.mkdtemp(prefix="astraea_ledger_test_")
        self.db_path = os.path.join(self.test_dir, "test_ledger.db")
        self.config = LedgerConfig(
            node_id="node_test",
            node_key_hex=DEFAULT_NODE_KEY_HEX,
            db_path=self.db_path,
            verify_signatures=False  # Allow flexible test signatures in mock env
        )
        self.engine = LedgerEngine(self.config)

    def tearDown(self):
        # Clean up temporary test files
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # =========================================================================
    # 1. GENESIS BLOCK INITIALIZATION TESTS
    # =========================================================================
    def test_genesis_block_creation(self):
        """Verify the genesis block is automatically created with standard constants."""
        genesis = self.engine.db.get_genesis_block()
        self.assertEqual(genesis["block_id"], 1)
        self.assertEqual(genesis["y_prev"], GENESIS_Y_PREV)
        self.assertEqual(genesis["mask"], GENESIS_MASK)
        self.assertEqual(genesis["client_signature"], GENESIS_SIGNATURE)
        self.assertEqual(genesis["client_receipt"], GENESIS_RECEIPT)
        self.assertEqual(genesis["y_current"], GENESIS_Y_CURRENT)
        
        # Verify BLAKE3 calculation of genesis hash
        expected_genesis = blake3(b"ASTRAEA_GENESIS_BLOCK").hexdigest()
        self.assertEqual(genesis["y_current"], expected_genesis)

    # =========================================================================
    # 2. REQUEST TO ADD A BLOCK TESTS
    # =========================================================================
    def test_add_single_block(self):
        """Verify requesting to add a block properly links to Genesis and calculates W_ID."""
        receipt = "OFFICER_ALPHA || DOC_SECRET_001 || 2026-09-25T17:30:00Z"
        test_sig = bytes.fromhex("11" * 32)

        resp = self.engine.commit_block(
            client_receipt=receipt,
            client_signature=test_sig
        )

        self.assertEqual(resp.status, "authorized")
        self.assertEqual(resp.block_id, 2)
        self.assertEqual(resp.y_prev, GENESIS_Y_CURRENT)
        self.assertEqual(len(resp.y_current), 64)
        self.assertEqual(len(resp.w_id), 64)

        # Independently verify the math matches MFHCEngine
        mfhc = MFHCEngine(self.config.node_key_hex)
        expected_mask = mfhc.generate_mask(GENESIS_Y_CURRENT).hex()
        expected_y_i = mfhc.commit_block(GENESIS_Y_CURRENT, test_sig, receipt)
        expected_wid = ForensicIDEngine.derive_forensic_id(test_sig, expected_y_i)

        self.assertEqual(resp.mask, expected_mask)
        self.assertEqual(resp.y_current, expected_y_i)
        self.assertEqual(resp.w_id, expected_wid)

    def test_add_sequential_blocks_chain_growth(self):
        """Verify sequential block additions maintain unbroken cryptographic chain continuity."""
        signatures = [bytes.fromhex(f"{i:02x}" * 32) for i in range(1, 6)]
        block_responses = []

        for i, sig in enumerate(signatures, start=1):
            receipt = f"OFFICER_{i:03d} || DOC_OPS_99 || 2026-09-25T17:3{i:01d}:00Z"
            resp = self.engine.commit_block(client_receipt=receipt, client_signature=sig)
            block_responses.append(resp)

        self.assertEqual(len(block_responses), 5)
        # Total blocks in DB should now be 1 (genesis) + 5 = 6
        self.assertEqual(self.engine.db.count_blocks(), 6)

        # Check hash chaining
        prev_hash = GENESIS_Y_CURRENT
        for idx, resp in enumerate(block_responses):
            self.assertEqual(resp.block_id, idx + 2)
            self.assertEqual(resp.y_prev, prev_hash)
            prev_hash = resp.y_current

    # =========================================================================
    # 3. TRAVERSE THE LEDGER BLOCKS TESTS
    # =========================================================================
    def test_traverse_blocks_ascending_and_descending(self):
        """Verify traversing ledger blocks from Genesis -> Head and Head -> Genesis."""
        # Add 3 blocks
        for i in range(1, 4):
            sig = bytes.fromhex(f"0{i}" * 32)
            self.engine.commit_block(
                client_receipt=f"OFFICER_{i} || DOC_X || 2026-09-25T18:0{i}:00Z",
                client_signature=sig
            )

        # Traverse Ascending (Genesis -> Head)
        traversal_asc = self.engine.traverse_blocks(reverse=False)
        self.assertEqual(traversal_asc.total_blocks, 4)
        self.assertEqual(len(traversal_asc.blocks), 4)
        self.assertEqual([b.block_id for b in traversal_asc.blocks], [1, 2, 3, 4])
        self.assertEqual(traversal_asc.order, "asc")

        # Traverse Descending (Head -> Genesis)
        traversal_desc = self.engine.traverse_blocks(reverse=True)
        self.assertEqual(traversal_desc.total_blocks, 4)
        self.assertEqual([b.block_id for b in traversal_desc.blocks], [4, 3, 2, 1])
        self.assertEqual(traversal_desc.order, "desc")

    def test_traverse_blocks_pagination(self):
        """Verify paginated traversal with offset and limit."""
        for i in range(1, 6):
            self.engine.commit_block(
                client_receipt=f"OFFICER_{i} || DOC_X || 2026-09-25T18:0{i}:00Z",
                client_signature=bytes.fromhex(f"0{i}" * 32)
            )

        # 6 total blocks (1 genesis + 5 created)
        page1 = self.engine.traverse_blocks(offset=0, limit=2, reverse=False)
        self.assertEqual(len(page1.blocks), 2)
        self.assertEqual([b.block_id for b in page1.blocks], [1, 2])

        page2 = self.engine.traverse_blocks(offset=2, limit=2, reverse=False)
        self.assertEqual(len(page2.blocks), 2)
        self.assertEqual([b.block_id for b in page2.blocks], [3, 4])

        page3 = self.engine.traverse_blocks(offset=4, limit=2, reverse=False)
        self.assertEqual(len(page3.blocks), 2)
        self.assertEqual([b.block_id for b in page3.blocks], [5, 6])

    def test_get_block_by_id_and_hash(self):
        """Verify direct block lookup by ID index and state hash."""
        sig = bytes.fromhex("44" * 32)
        resp = self.engine.commit_block(
            client_receipt="OFFICER_44 || DOC_TACTICAL || 2026-09-25T18:44:00Z",
            client_signature=sig
        )

        # Lookup by ID
        block_by_id = self.engine.get_block_by_id(2)
        self.assertIsNotNone(block_by_id)
        self.assertEqual(block_by_id.y_current, resp.y_current)

        # Lookup by hash
        block_by_hash = self.engine.get_block_by_hash(resp.y_current)
        self.assertIsNotNone(block_by_hash)
        self.assertEqual(block_by_hash.block_id, 2)

    # =========================================================================
    # 4. CRYPTOGRAPHIC CHAIN INTEGRITY & TAMPER DETECTION TESTS
    # =========================================================================
    def test_chain_integrity_on_valid_ledger(self):
        """Verify that a pristine ledger passes cryptographic integrity traversal."""
        for i in range(1, 4):
            self.engine.commit_block(
                client_receipt=f"OFFICER_{i} || DOC_VALID || 2026-09-25T19:0{i}:00Z",
                client_signature=bytes.fromhex(f"0{i}" * 32)
            )

        report = self.engine.verify_chain_integrity()
        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_blocks, 4)
        self.assertIsNone(report.broken_at_block_id)
        self.assertIsNotNone(report.head_hash)

    def test_tamper_detection_modified_receipt(self):
        """Verify that altering a receipt in SQLite causes immediate state avalanche failure."""
        for i in range(1, 4):
            self.engine.commit_block(
                client_receipt=f"OFFICER_{i} || DOC_TOPSECRET || 2026-09-25T19:0{i}:00Z",
                client_signature=bytes.fromhex(f"0{i}" * 32)
            )

        # Rogue administrator modifies row 2 directly in SQLite
        with self.engine.db.get_connection() as conn:
            conn.execute(
                "UPDATE blocks SET client_receipt = 'ROGUE_ADMIN || DOC_FORGED || 2026-09-25' WHERE block_id = 2;"
            )
            conn.commit()

        # Audit should instantly catch the tamper attempt and pinpoint block 2
        report = self.engine.verify_chain_integrity()
        self.assertFalse(report.is_valid)
        self.assertEqual(report.broken_at_block_id, 2)
        self.assertIn("avalanche failed", report.error_reason.lower())

    def test_tamper_detection_broken_chain_continuity(self):
        """Verify that altering y_prev or dropping a block triggers continuity breach."""
        for i in range(1, 4):
            self.engine.commit_block(
                client_receipt=f"OFFICER_{i} || DOC_DATA || 2026-09-25T19:0{i}:00Z",
                client_signature=bytes.fromhex(f"0{i}" * 32)
            )

        # Maliciously delete Block #2
        with self.engine.db.get_connection() as conn:
            conn.execute("DELETE FROM blocks WHERE block_id = 2;")
            conn.commit()

        report = self.engine.verify_chain_integrity()
        self.assertFalse(report.is_valid)
        self.assertEqual(report.broken_at_block_id, 3)
        self.assertIn("continuity broken", report.error_reason.lower())

    # =========================================================================
    # 5. FORENSIC WATERMARK ATTRIBUTION TESTS
    # =========================================================================
    def test_forensic_audit_lookup_successful(self):
        """Verify reverse lookup finds the exact officer from an extracted W_ID."""
        sig1 = bytes.fromhex("aa" * 32)
        sig2 = bytes.fromhex("bb" * 32)

        resp1 = self.engine.commit_block(
            client_receipt="OFFICER_RED || DOC_BLUEPRINT_99 || 2026-09-25T20:00:00Z",
            client_signature=sig1
        )
        resp2 = self.engine.commit_block(
            client_receipt="OFFICER_BLUE || DOC_BLUEPRINT_99 || 2026-09-25T20:05:00Z",
            client_signature=sig2
        )

        # Investigator extracts Officer Blue's watermark ID from a photograph
        extracted_wid = resp2.w_id

        audit_res = self.engine.audit_forensic_wid(extracted_wid)
        self.assertEqual(audit_res.attribution_status, "FOUND")
        self.assertEqual(audit_res.block_id, 3)
        self.assertEqual(audit_res.parsed_receipt["uid"], "OFFICER_BLUE")
        self.assertEqual(audit_res.parsed_receipt["doc_id"], "DOC_BLUEPRINT_99")
        self.assertTrue(audit_res.signature_verified)

    def test_forensic_audit_unknown_watermark(self):
        """Verify unknown watermark returns NOT_FOUND."""
        bogus_wid = "ff" * 32
        audit_res = self.engine.audit_forensic_wid(bogus_wid)
        self.assertEqual(audit_res.attribution_status, "NOT_FOUND")

    # =========================================================================
    # 6. CONSENSUS COORDINATOR TESTS (3-NODE SIMULATION)
    # =========================================================================
    def test_consensus_majority_agreement(self):
        """Verify 3-node consortium consensus achieves agreement and authorizes key release."""
        import asyncio

        cluster_dir = os.path.join(self.test_dir, "cluster")
        coordinator = ConsensusCoordinator.create_in_memory_or_local_cluster(cluster_dir)

        receipt = "OFFICER_COMMANDER || WAR_PLAN_2026 || 2026-09-25T21:00:00Z"
        sig = bytes.fromhex("cc" * 32)

        result = asyncio.run(coordinator.commit_distributed(receipt, sig))
        self.assertTrue(result.consensus_achieved)
        self.assertEqual(result.quorum_fraction, "3/3")
        self.assertTrue(result.authorization_granted)
        self.assertEqual(len(result.agreeing_nodes), 3)

    # =========================================================================
    # 7. FASTAPI REST INTERFACE TESTS
    # =========================================================================
    def test_fastapi_endpoints(self):
        """Verify REST API endpoints for commit, traversal, verification, and audit."""
        app = create_ledger_app(self.config)
        client = TestClient(app)

        # Health / Status
        status_res = client.get("/ledger/status")
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(status_res.json()["node_id"], "node_test")
        self.assertEqual(status_res.json()["head_block_id"], 1)

        # Commit Block
        commit_payload = {
            "client_receipt": "OFFICER_API || DOC_API_TEST || 2026-09-25T22:00:00Z",
            "client_signature": ("ee" * 32)
        }
        commit_res = client.post("/ledger/commit", json=commit_payload)
        self.assertEqual(commit_res.status_code, 200)
        commit_data = commit_res.json()
        self.assertEqual(commit_data["status"], "authorized")
        self.assertEqual(commit_data["block_id"], 2)
        wid = commit_data["w_id"]

        # Traverse Blocks
        blocks_res = client.get("/ledger/blocks?offset=0&limit=10")
        self.assertEqual(blocks_res.status_code, 200)
        traversal_data = blocks_res.json()
        self.assertEqual(traversal_data["total_blocks"], 2)
        self.assertEqual(len(traversal_data["blocks"]), 2)

        # Traverse Single Block
        single_res = client.get("/ledger/blocks/2")
        self.assertEqual(single_res.status_code, 200)
        self.assertEqual(single_res.json()["block_id"], 2)

        # Verify Integrity
        verify_res = client.get("/ledger/verify")
        self.assertEqual(verify_res.status_code, 200)
        self.assertTrue(verify_res.json()["is_valid"])

        # Forensic Audit
        audit_res = client.post("/ledger/audit", json={"extracted_wid": wid})
        self.assertEqual(audit_res.status_code, 200)
        self.assertEqual(audit_res.json()["attribution_status"], "FOUND")
        self.assertEqual(audit_res.json()["parsed_receipt"]["uid"], "OFFICER_API")


if __name__ == "__main__":
    unittest.main()
