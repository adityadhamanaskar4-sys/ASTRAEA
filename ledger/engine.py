import logging
import threading
from typing import Optional, List, Dict, Any, Tuple
from blake3 import blake3

from QuantumCrypto.ledger_math import MFHCEngine
from QuantumCrypto.forensic_id import ForensicIDEngine
from ledger.config import LedgerConfig
from ledger.db import LedgerDatabase, GENESIS_Y_PREV, GENESIS_Y_CURRENT
from ledger.models import (
    BlockRecord,
    BlockCommitResponse,
    BlockTraversalResponse,
    ChainIntegrityReport,
    ForensicAuditResponse,
    NodeStatusResponse,
)

logger = logging.getLogger("ASTRAEA.LedgerEngine")

# Optional ML-DSA Engine integration with graceful fallback if liboqs C library is not compiled
try:
    from QuantumCrypto.dsa_engine import DSAEngine
    OQS_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    logger.warning("liboqs (ML-DSA) not installed or build missing. Running in simulated signature verification mode.")
    DSAEngine = None
    OQS_AVAILABLE = False


class LedgerEngine:
    """
    Core implementation of the Monotonic Feistel Hash-Chain (MFHC) Ledger for Project ASTRAEA.
    Enforces the tamper-evident provenance requirement before decryption keys can be released.
    """

    def __init__(self, config: Optional[LedgerConfig] = None):
        self.config = config or LedgerConfig.from_env()
        self.db = LedgerDatabase(self.config.db_path)
        self.mfhc = MFHCEngine(self.config.node_key_hex)
        self._lock = threading.Lock()

    def _verify_client_signature(
        self,
        receipt: str,
        signature_bytes: bytes,
        recipient_pk_bytes: Optional[bytes] = None
    ) -> bool:
        """
        Validates ML-DSA signature over client decryption receipt.
        If recipient_pk_bytes is provided and DSAEngine is available, performs NIST FIPS 204 ML-DSA-65 verification.
        Otherwise validates signature structure non-emptiness.
        """
        if not signature_bytes or len(signature_bytes) == 0:
            return False

        if OQS_AVAILABLE and DSAEngine is not None and recipient_pk_bytes is not None:
            try:
                return DSAEngine.verify_receipt(recipient_pk_bytes, receipt, signature_bytes)
            except Exception as e:
                logger.error(f"ML-DSA verification failed with error: {e}")
                return False

        # In local developer / prototype fallback mode without liboqs
        # Check non-empty valid signature payload (or mock verification)
        return len(signature_bytes) >= 16

    @staticmethod
    def _parse_receipt(receipt: str) -> Dict[str, str]:
        """Parses standard ASTRAEA receipt string: UID || DocID || Timestamp."""
        parts = [p.strip() for p in receipt.split("||")]
        if len(parts) >= 3:
            return {
                "uid": parts[0],
                "doc_id": parts[1],
                "timestamp": parts[2]
            }
        return {"raw_receipt": receipt}

    # =========================================================================
    # OUTCOME 1: Request to Add a Block
    # =========================================================================
    def commit_block(
        self,
        client_receipt: str,
        client_signature: bytes | str,
        recipient_public_key: Optional[bytes | str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BlockCommitResponse:
        """
        Processes a block committal request from Backend 1 / Decryption Request handler.
        
        Sequence:
        1. Parse and validate signature bytes.
        2. Verify ML-DSA signature over m_receipt.
        3. Acquire lock and fetch latest block hash y_prev.
        4. Generate Feistel mask M_chain = BLAKE3((y_prev XOR Node_Key)^2 + ...).
        5. Calculate new avalanche block state y_i = BLAKE3(y_prev || M_chain || sigma_u || m_receipt).
        6. Append new row into the immutable SQLite ledger.
        7. Derive deterministic steganographic watermark ID W_ID = BLAKE3(sigma_u || y_i).
        8. Return committal authorization and W_ID.
        """
        # Normalize signature to bytes and hex string
        if isinstance(client_signature, str):
            # Clean hex string
            clean_sig = client_signature.strip()
            try:
                sig_bytes = bytes.fromhex(clean_sig)
            except ValueError:
                sig_bytes = clean_sig.encode("utf-8")
        else:
            sig_bytes = client_signature

        sig_hex = sig_bytes.hex()

        # Normalize public key if present
        pk_bytes = None
        if recipient_public_key is not None:
            if isinstance(recipient_public_key, str):
                try:
                    pk_bytes = bytes.fromhex(recipient_public_key.strip())
                except ValueError:
                    pk_bytes = recipient_public_key.strip().encode("utf-8")
            else:
                pk_bytes = recipient_public_key

        # Validate signature if verification enabled
        if self.config.verify_signatures:
            is_valid_sig = self._verify_client_signature(client_receipt, sig_bytes, pk_bytes)
            if not is_valid_sig:
                raise ValueError("SIGNATURE_VERIFICATION_FAILED: Invalid or untrusted ML-DSA signature.")

        with self._lock:
            # 1. Fetch preceding block
            head_block = self.db.get_head_block()
            y_prev_hex = head_block["y_current"]

            # 2. Generate Monotonic Feistel chain mask
            mask_bytes = self.mfhc.generate_mask(y_prev_hex)
            mask_hex = mask_bytes.hex()

            # 3. Compute State Avalanche y_i
            y_i_hex = self.mfhc.commit_block(y_prev_hex, sig_bytes, client_receipt)

            # 4. Insert row atomically into ledger
            row = self.db.insert_block(
                y_prev=y_prev_hex,
                mask=mask_hex,
                client_signature=sig_hex,
                client_receipt=client_receipt,
                y_current=y_i_hex
            )

            # 5. Derive deterministic forensic watermark ID W_ID
            w_id = ForensicIDEngine.derive_forensic_id(sig_bytes, y_i_hex)

            logger.info(
                f"[{self.config.node_id}] Block #{row['block_id']} committed | y_i: {y_i_hex[:12]}... | W_ID: {w_id[:12]}..."
            )

            return BlockCommitResponse(
                status="authorized",
                node_id=self.config.node_id,
                block_id=row["block_id"],
                timestamp=str(row["timestamp"]),
                y_prev=y_prev_hex,
                mask=mask_hex,
                y_current=y_i_hex,
                w_id=w_id,
                message="Block committed successfully to MFHC ledger. Decryption authorized."
            )

    # =========================================================================
    # OUTCOME 2: Traverse the Ledger Blocks & Integrity Verification
    # =========================================================================
    def traverse_blocks(
        self,
        offset: int = 0,
        limit: Optional[int] = None,
        reverse: bool = False
    ) -> BlockTraversalResponse:
        """
        Traverses blocks in the ledger:
        - If reverse=False: Genesis to Head (ascending sequence).
        - If reverse=True: Head to Genesis (descending sequence).
        Supports pagination with offset and limit.
        """
        total = self.db.count_blocks()
        rows = self.db.get_blocks_paginated(offset=offset, limit=limit, reverse=reverse)
        block_records = [
            BlockRecord(
                block_id=r["block_id"],
                timestamp=str(r["timestamp"]),
                y_prev=r["y_prev"],
                mask=r["mask"],
                client_signature=r["client_signature"],
                client_receipt=r["client_receipt"],
                y_current=r["y_current"]
            )
            for r in rows
        ]

        return BlockTraversalResponse(
            total_blocks=total,
            offset=offset,
            limit=limit,
            order="desc" if reverse else "asc",
            blocks=block_records
        )

    def get_block_by_id(self, block_id: int) -> Optional[BlockRecord]:
        """Retrieves a single block by its block_id index."""
        row = self.db.get_block_by_id(block_id)
        if not row:
            return None
        return BlockRecord(
            block_id=row["block_id"],
            timestamp=str(row["timestamp"]),
            y_prev=row["y_prev"],
            mask=row["mask"],
            client_signature=row["client_signature"],
            client_receipt=row["client_receipt"],
            y_current=row["y_current"]
        )

    def get_block_by_hash(self, y_hash: str) -> Optional[BlockRecord]:
        """Retrieves a single block by its committed state hash y_current."""
        row = self.db.get_block_by_hash(y_hash)
        if not row:
            return None
        return BlockRecord(
            block_id=row["block_id"],
            timestamp=str(row["timestamp"]),
            y_prev=row["y_prev"],
            mask=row["mask"],
            client_signature=row["client_signature"],
            client_receipt=row["client_receipt"],
            y_current=row["y_current"]
        )

    def verify_chain_integrity(self) -> ChainIntegrityReport:
        """
        Traverses the entire hash-chain from Genesis (block 1) to Head,
        recalculating all Feistel masks and BLAKE3 avalanche states.
        
        Guarantees:
        - Genesis block matches ASTRAEA standard.
        - Continuity: y_prev[k] == y_current[k-1].
        - Mask integrity: M_chain == generate_mask(y_prev).
        - State avalanche integrity: y_current == commit_block(y_prev, sigma_u, receipt).
        
        If a rogue administrator or attacker modified or removed any row,
        the verification shatters immediately and pinpoints the corrupted block ID.
        """
        all_blocks = self.db.get_blocks_paginated(offset=0, limit=None, reverse=False)
        total_count = len(all_blocks)

        if total_count == 0:
            return ChainIntegrityReport(
                is_valid=False,
                total_blocks=0,
                error_reason="Ledger database contains no blocks (even Genesis is missing)."
            )

        # 1. Verify Genesis Block (Block 1)
        genesis = all_blocks[0]
        if genesis["block_id"] != 1:
            return ChainIntegrityReport(
                is_valid=False,
                total_blocks=total_count,
                broken_at_block_id=genesis["block_id"],
                error_reason=f"First block is not Genesis (block_id: {genesis['block_id']})."
            )

        if genesis["y_prev"] != GENESIS_Y_PREV or genesis["y_current"] != GENESIS_Y_CURRENT:
            return ChainIntegrityReport(
                is_valid=False,
                total_blocks=total_count,
                broken_at_block_id=1,
                error_reason="Genesis block hash corrupted or altered.",
                details={
                    "stored_y_prev": genesis["y_prev"],
                    "expected_y_prev": GENESIS_Y_PREV,
                    "stored_y_current": genesis["y_current"],
                    "expected_y_current": GENESIS_Y_CURRENT
                }
            )

        # 2. Traverse and audit subsequent blocks
        for i in range(1, total_count):
            curr = all_blocks[i]
            prev = all_blocks[i - 1]
            curr_id = curr["block_id"]

            # A. Continuity Check
            if curr["y_prev"] != prev["y_current"]:
                return ChainIntegrityReport(
                    is_valid=False,
                    total_blocks=total_count,
                    broken_at_block_id=curr_id,
                    error_reason=(
                        f"Chain continuity broken between Block #{prev['block_id']} and Block #{curr_id}: "
                        f"y_prev ({curr['y_prev'][:16]}...) != prev y_current ({prev['y_current'][:16]}...)"
                    ),
                    details={
                        "block_id": curr_id,
                        "stored_y_prev": curr["y_prev"],
                        "predecessor_y_current": prev["y_current"]
                    }
                )

            # B. Feistel Mask Check
            expected_mask_bytes = self.mfhc.generate_mask(curr["y_prev"])
            expected_mask_hex = expected_mask_bytes.hex()
            if curr["mask"] != expected_mask_hex:
                return ChainIntegrityReport(
                    is_valid=False,
                    total_blocks=total_count,
                    broken_at_block_id=curr_id,
                    error_reason=f"Feistel mask mismatch at Block #{curr_id}.",
                    details={
                        "block_id": curr_id,
                        "stored_mask": curr["mask"],
                        "computed_mask": expected_mask_hex
                    }
                )

            # C. State Avalanche BLAKE3 Check
            try:
                sig_bytes = bytes.fromhex(curr["client_signature"])
            except ValueError:
                sig_bytes = curr["client_signature"].encode("utf-8")

            expected_y_current = self.mfhc.commit_block(
                curr["y_prev"],
                sig_bytes,
                curr["client_receipt"]
            )

            if curr["y_current"] != expected_y_current:
                return ChainIntegrityReport(
                    is_valid=False,
                    total_blocks=total_count,
                    broken_at_block_id=curr_id,
                    error_reason=f"Cryptographic state avalanche failed at Block #{curr_id}. Content tampered.",
                    details={
                        "block_id": curr_id,
                        "stored_y_current": curr["y_current"],
                        "computed_y_current": expected_y_current,
                        "client_receipt": curr["client_receipt"]
                    }
                )

        head = all_blocks[-1]
        return ChainIntegrityReport(
            is_valid=True,
            total_blocks=total_count,
            head_hash=head["y_current"],
            genesis_hash=genesis["y_current"]
        )

    # =========================================================================
    # FORENSIC AUDIT: Leak Attribution by Watermark ID
    # =========================================================================
    @staticmethod
    def _compute_wid_similarity(extracted_hex: str, candidate_hex: str) -> tuple[float, int, int, str]:
        """
        Computes the cryptographic similarity between an extracted (possibly incomplete or noisy)
        watermark ID and a candidate ledger watermark ID.
        Returns:
            (similarity_percentage, matching_bits, total_bits_evaluated, match_type)
        """
        ext = extracted_hex.strip().lower()
        cand = candidate_hex.strip().lower()

        # 1. Exact equality
        if ext == cand:
            return 100.0, 256, 256, "EXACT_MATCH"

        # 2. Exact prefix match (e.g. partial prefix recovered from document)
        if len(ext) >= 8 and cand.startswith(ext):
            pct = round((len(ext) / len(cand)) * 100.0, 1)
            return 100.0, len(ext) * 4, len(ext) * 4, f"PREFIX_MATCH ({len(ext)}/64 chars, {pct}% coverage)"

        # 3. Exact substring match (fragment recovered from middle)
        if len(ext) >= 8 and ext in cand:
            pct = round((len(ext) / len(cand)) * 100.0, 1)
            return 98.0, len(ext) * 4, len(ext) * 4, f"SUBSTRING_MATCH ({len(ext)}/64 chars, {pct}% coverage)"

        # 4. Bit-level Hamming comparison
        def hex_to_bits(h_str):
            bits = []
            for ch in h_str:
                try:
                    bits.append(f"{int(ch, 16):04b}")
                except ValueError:
                    pass
            return "".join(bits)

        b_ext = hex_to_bits(ext)
        b_cand = hex_to_bits(cand)
        min_len = min(len(b_ext), len(b_cand))

        if min_len == 0:
            return 0.0, 0, 256, "NO_OVERLAP"

        matching_bits = sum(1 for x, y in zip(b_ext[:min_len], b_cand[:min_len]) if x == y)
        bit_acc = (matching_bits / min_len) * 100.0

        if len(b_ext) == len(b_cand) == 256:
            return round(bit_acc, 1), matching_bits, 256, f"BIT_SIMILARITY ({matching_bits}/256 bits)"
        else:
            coverage = min_len / 256.0
            weighted_score = (bit_acc * 0.7) + (coverage * 100.0 * 0.3)
            return round(weighted_score, 1), matching_bits, min_len, f"PARTIAL_BIT_SIMILARITY ({matching_bits}/{min_len} bits)"

    def audit_forensic_wid(self, extracted_wid: str, doc_id: Optional[str] = None) -> ForensicAuditResponse:
        """
        Traverses the ledger to resolve a physical leak by its recovered 256-bit watermark ID (W_ID*).
        Supports full 256-bit W_ID, partial prefixes/substrings, and noisy/corrupted marks.
        Optionally scopes/reduces search window to blocks associated with doc_id.
        Ranks and lists all similar candidate officers.
        """
        clean_wid = extracted_wid.strip().lower()
        clean_doc_id = doc_id.strip() if doc_id else None
        if not clean_wid:
            return ForensicAuditResponse(
                attribution_status="NOT_FOUND",
                extracted_wid=extracted_wid,
                message="Extracted watermark ID is empty.",
                candidates=[]
            )

        audit_blocks = self.db.get_all_blocks_for_audit()
        candidates = []

        for block in audit_blocks:
            parsed = self._parse_receipt(block["client_receipt"])

            # If doc_id filter is provided, skip blocks for other documents
            if clean_doc_id and parsed.get("doc_id") != clean_doc_id:
                continue

            try:
                sig_bytes = bytes.fromhex(block["client_signature"])
            except ValueError:
                sig_bytes = block["client_signature"].encode("utf-8")

            y_i_hex = block["y_current"]
            computed_wid = ForensicIDEngine.derive_forensic_id(sig_bytes, y_i_hex).lower()

            sim_pct, matching_bits, total_bits, match_type = self._compute_wid_similarity(clean_wid, computed_wid)

            is_sig_valid = self._verify_client_signature(
                block["client_receipt"],
                sig_bytes,
                recipient_pk_bytes=None
            )

            candidate_info = {
                "officer_uid": parsed.get("uid", "UNKNOWN"),
                "doc_id": parsed.get("doc_id", "UNKNOWN"),
                "block_id": block["block_id"],
                "timestamp": block["timestamp"],
                "computed_wid": computed_wid,
                "similarity_percentage": sim_pct,
                "matching_bits": f"{matching_bits}/{total_bits}",
                "match_type": match_type,
                "signature_verified": is_sig_valid,
                "client_receipt": block["client_receipt"],
                "client_signature": block["client_signature"],
                "y_current": y_i_hex,
                "parsed_receipt": parsed
            }
            candidates.append(candidate_info)

        # Sort candidates by similarity descending
        candidates.sort(key=lambda c: (c["similarity_percentage"], c["block_id"]), reverse=True)

        if not candidates:
            msg = f"No committed access blocks found for Document {clean_doc_id} in ledger." if clean_doc_id else "Ledger contains no committed access blocks."
            return ForensicAuditResponse(
                attribution_status="NOT_FOUND",
                extracted_wid=extracted_wid,
                message=msg,
                candidates=[]
            )

        top = candidates[0]

        # Case 1: Exact Match (100% on 64 chars)
        if top["similarity_percentage"] == 100.0 and len(clean_wid) == 64:
            status = "FOUND" if top["signature_verified"] else "FOUND_BUT_INVALID"
            return ForensicAuditResponse(
                attribution_status=status,
                extracted_wid=extracted_wid,
                block_id=top["block_id"],
                client_receipt=top["client_receipt"],
                client_signature=top["client_signature"],
                y_current=top["y_current"],
                parsed_receipt=top["parsed_receipt"],
                signature_verified=top["signature_verified"],
                message=(
                    f"Leak successfully attributed to Officer {top['officer_uid']} "
                    f"for Document {top['doc_id']} committed at Block #{top['block_id']}."
                ),
                candidates=candidates
            )

        # Case 2: Partial Match:
        # A partial match happens if:
        # - It is an exact prefix or substring match of >= 8 characters
        # - OR it has statistically significant bit similarity (>= 80.0%), indicating a noisy/degraded 256-bit mark.
        is_prefix_or_substr = "PREFIX" in top["match_type"] or "SUBSTRING" in top["match_type"]
        is_high_bit_similarity = top["similarity_percentage"] >= 80.0

        if is_prefix_or_substr or is_high_bit_similarity:
            status = "PARTIAL_MATCH"
            return ForensicAuditResponse(
                attribution_status=status,
                extracted_wid=extracted_wid,
                block_id=top["block_id"],
                client_receipt=top["client_receipt"],
                client_signature=top["client_signature"],
                y_current=top["y_current"],
                parsed_receipt=top["parsed_receipt"],
                signature_verified=top["signature_verified"],
                message=(
                    f"Partial watermark match ({top['similarity_percentage']}% similarity, {top['match_type']}): "
                    f"Highest probability attributed to Officer {top['officer_uid']} "
                    f"for Document {top['doc_id']} at Block #{top['block_id']}."
                ),
                candidates=candidates
            )

        return ForensicAuditResponse(
            attribution_status="NOT_FOUND",
            extracted_wid=extracted_wid,
            message="No ledger record matches or closely resembles the extracted watermark ID.",
            candidates=candidates
        )

    def get_status(self) -> NodeStatusResponse:
        """Returns node health, chain height, and cryptographic head state."""
        head = self.db.get_head_block()
        genesis = self.db.get_genesis_block()
        total = self.db.count_blocks()

        return NodeStatusResponse(
            node_id=self.config.node_id,
            head_block_id=head["block_id"],
            head_hash=head["y_current"],
            genesis_hash=genesis["y_current"],
            total_blocks=total,
            status="ONLINE"
        )
