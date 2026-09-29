import io
import time
import uuid
import base64
import logging
from typing import Dict, Any, List, Optional
import numpy as np
import cv2

from backend.crypto_interface import CryptoWrapper
from backend.ledger_interface import LedgerService
from backend.watermark_interface import WatermarkIDService, DWTWatermarkEngine
from backend.services.state_machine import PipelineStateMachine
from backend.database.sqlite_store import SQLiteStore
from backend.models.state import PipelineStage, AuditStatus
from backend.models.requests import BroadcastRequest, DecryptionRequest, AuditRequest
from backend.models.responses import (
    BroadcastResponse,
    RecipientLockbox,
    DecryptionResponse,
    AuditResponse,
    DocumentMetadataResponse,
)

logger = logging.getLogger("ASTRAEA.PipelineService")


class ASTRAEAPipelineService:
    """
    Master Pipeline Service for Project ASTRAEA Backend 1.
    Connects:
    Frontend <-> API <-> Cryptography <-> DLT (Backend 2) <-> Watermarking <-> Forensic Audit.
    All data is persisted in SQLite databases running in offline airgapped mode.
    """

    def __init__(self, db_path: str = "astraea_ledger.db"):
        self.db_path = db_path
        self.ledger_service = LedgerService(db_path=db_path)
        self.watermark_engine = DWTWatermarkEngine()
        self.wid_service = WatermarkIDService()
        self.sqlite_store = SQLiteStore(db_path=db_path)
        self.sqlite_store.seed_sample_users(CryptoWrapper)
        
        # In-memory document cache initialized from SQLite
        self._documents: Dict[str, Dict[str, Any]] = {}
        for doc in self.sqlite_store.get_all_documents():
            self._documents[doc["doc_id"]] = doc
            
        # Recipient keypair cache for simulation (uid -> {pk_kem, sk_kem, pk_dsa, sk_dsa})
        self._recipient_keys: Dict[str, Dict[str, bytes]] = {}

    def _get_or_create_recipient_keys(self, uid: str) -> Dict[str, bytes]:
        """Retrieves or generates cached ML-KEM and ML-DSA keys for recipient officer from SQLite."""
        if uid in self._recipient_keys:
            return self._recipient_keys[uid]

        keys = self.sqlite_store.get_user_keys(uid)
        if keys:
            self._recipient_keys[uid] = keys
            return keys

        pk_kem, sk_kem = CryptoWrapper.generate_kem_keypair()
        pk_dsa, sk_dsa = CryptoWrapper.generate_dsa_keypair()
        keys = {
            "pk_kem": pk_kem,
            "sk_kem": sk_kem,
            "pk_dsa": pk_dsa,
            "sk_dsa": sk_dsa
        }
        self.sqlite_store.save_user_keys(
            uid=uid,
            name=f"Officer {uid}",
            role="Recipient",
            clearance_level="RESTRICTED",
            keys=keys
        )
        self._recipient_keys[uid] = keys
        return self._recipient_keys[uid]

    def list_users(self) -> List[Dict[str, Any]]:
        """Returns all registered users from SQLite."""
        return self.sqlite_store.get_all_users()

    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        """Returns specific user profile from SQLite."""
        return self.sqlite_store.get_user(uid)

    def get_user_keys(self, uid: str) -> Optional[Dict[str, bytes]]:
        """Returns recipient cryptographic keys."""
        return self._get_or_create_recipient_keys(uid)

    # =========================================================================
    # PHASE 1: DOCUMENT BROADCAST & ENCRYPTION
    # =========================================================================
    def broadcast_document(self, req: BroadcastRequest) -> BroadcastResponse:
        """
        Receives document plaintext, generates random K_doc, encrypts using AES-256-GCM,
        and encapsulates K_doc into ML-KEM lockboxes for each recipient.
        """
        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        plaintext_bytes = req.body.encode("utf-8")

        # 1. AES-256-GCM Encryption
        K_doc, encrypted_payload = CryptoWrapper.encrypt_payload(plaintext_bytes)

        # 2. Per-recipient ML-KEM Encapsulation & Key Wrapping
        recipients_list: List[RecipientLockbox] = []
        lockboxes_data: Dict[str, Dict[str, Any]] = {}

        for uid in req.recipient_uids:
            keys = self._get_or_create_recipient_keys(uid)
            c_u, K_shared = CryptoWrapper.encapsulate_kem(keys["pk_kem"])
            
            # Wrap K_doc using AES-WRAP with K_shared
            from QuantumCrypto.aes_engine import AESEngine
            W_u = AESEngine.wrap_key(K_shared, K_doc)

            lockbox_ref = f"LB-{uuid.uuid4().hex[:6].upper()}"
            lockbox_model = RecipientLockbox(
                uid=uid,
                name=f"Officer {uid}",
                lockbox_ref=lockbox_ref,
                c_u_hex=c_u.hex(),
                status="delivered"
            )
            recipients_list.append(lockbox_model)

            lockboxes_data[uid] = {
                "lockbox_ref": lockbox_ref,
                "c_u": c_u,
                "W_u": W_u,
                "status": "delivered"
            }

        # Ciphertext fingerprint (SHA-256 of encrypted payload)
        import hashlib
        ciphertext_fp = f"0x{hashlib.sha256(encrypted_payload).hexdigest()[:16].upper()}"
        created_at = time.time() * 1000

        # Store in-memory and persist encrypted document record in SQLite
        doc_entry = {
            "doc_id": doc_id,
            "title": req.title,
            "classification": req.classification,
            "plaintext_body": req.body,
            "encrypted_payload": encrypted_payload,
            "K_doc": K_doc,
            "ciphertext_fp": ciphertext_fp,
            "created_at": created_at,
            "lockboxes": lockboxes_data,
            "recipients": recipients_list
        }
        self._documents[doc_id] = doc_entry
        self.sqlite_store.save_document(doc_entry)

        logger.info(f"Broadcast created document {doc_id} with {len(req.recipient_uids)} recipient lockboxes (persisted to SQLite).")

        return BroadcastResponse(
            doc_id=doc_id,
            title=req.title,
            classification=req.classification,
            ciphertext_fp=ciphertext_fp,
            created_at=created_at,
            recipients=recipients_list
        )

    # =========================================================================
    # PHASE 2 - 6: DECRYPTION REQUEST & LEDGER-GATED KEY RELEASE
    # =========================================================================
    async def process_decryption_request(self, req: DecryptionRequest) -> DecryptionResponse:
        """
        Executes complete dynamic state sequence:
        REQUESTED -> SIGNATURE_VERIFIED -> LEDGER_PENDING -> LEDGER_COMMITTED
        -> TOKEN_RELEASED -> DECRYPTED -> WATERMARKED -> DELIVERED.
        
        Key release is strictly blocked until DLT commitment succeeds.
        """
        doc_entry = self._documents.get(req.doc_id)
        if not doc_entry:
            raise ValueError(f"UNKNOWN_DOC_ID: Document {req.doc_id} not found.")

        lockbox = doc_entry["lockboxes"].get(req.uid)
        if not lockbox:
            raise ValueError(f"UNAUTHORIZED_RECIPIENT: No lockbox for officer {req.uid} on doc {req.doc_id}.")

        session_id = f"SES-{uuid.uuid4().hex[:6].upper()}"
        sm = PipelineStateMachine(req.doc_id, req.uid, session_id)

        # Stage 1: REQUESTED -> SIGNATURE_VERIFIED
        m_receipt = f"{req.uid} || {req.doc_id} || {req.timestamp}"
        
        try:
            sig_bytes = bytes.fromhex(req.signature.strip())
        except ValueError:
            sig_bytes = req.signature.encode("utf-8")

        pk_dsa_bytes = None
        if req.recipient_pk:
            try:
                pk_dsa_bytes = bytes.fromhex(req.recipient_pk.strip())
            except ValueError:
                pk_dsa_bytes = req.recipient_pk.encode("utf-8")
        else:
            keys = self._get_or_create_recipient_keys(req.uid)
            pk_dsa_bytes = keys["pk_dsa"]

        is_sig_valid = CryptoWrapper.verify_receipt(pk_dsa_bytes, m_receipt, sig_bytes)
        if not is_sig_valid:
            sm.fail("INVALID_SIGNATURE: ML-DSA receipt signature verification failed.")
            raise ValueError("INVALID_SIGNATURE: ML-DSA signature verification failed.")

        sm.transition_to(PipelineStage.SIGNATURE_VERIFIED, f"ML-DSA-65 signature verified over m_receipt ({m_receipt[:30]}...)")

        # Stage 2: LEDGER_PENDING -> LEDGER_COMMITTED
        sm.transition_to(PipelineStage.LEDGER_PENDING, "Submitting transaction to DLT 3-Node Consensus Cluster...")

        commit_res = await self.ledger_service.commit_decryption_receipt(
            receipt_str=m_receipt,
            signature=sig_bytes,
            recipient_pk=pk_dsa_bytes
        )

        if not commit_res.get("authorization_granted") or not commit_res.get("consensus_achieved"):
            sm.fail(f"CONSENSUS_FAILURE: DLT committal failed. {commit_res.get('message')}")
            raise RuntimeError(f"DLT_COMMIT_FAILED: {commit_res.get('message')}")

        w_id = commit_res["w_id"]
        y_current = commit_res["y_current"]

        sm.transition_to(
            PipelineStage.LEDGER_COMMITTED,
            f"DLT Consensus Achieved ({commit_res['quorum_fraction']}). Block #{commit_res['block_id']} committed | y_i: {y_current[:12]}..."
        )

        # Stage 3: TOKEN_RELEASED (KEY RELEASE GUARD)
        sm.transition_to(PipelineStage.TOKEN_RELEASED, "Ledger commit verified. Releasing AES-256 payload key.")

        # Stage 4: DECRYPTED (In-memory BytesIO handling)
        keys = self._get_or_create_recipient_keys(req.uid)
        K_shared = CryptoWrapper.decapsulate_kem(keys["sk_kem"], lockbox["c_u"])
        
        from QuantumCrypto.aes_engine import AESEngine
        recovered_K_doc = AESEngine.unwrap_key(K_shared, lockbox["W_u"])

        # Perform in-memory decryption
        encrypted_payload = doc_entry["encrypted_payload"]
        plaintext_bytes = CryptoWrapper.decrypt_payload(recovered_K_doc, encrypted_payload)
        
        # Use io.BytesIO for memory stream buffer compliance
        buffer = io.BytesIO(plaintext_bytes)
        decrypted_text = buffer.getvalue().decode("utf-8")

        sm.transition_to(PipelineStage.DECRYPTED, "In-memory payload decryption complete.")

        # Stage 5: WATERMARKED (DWT Steganography)
        watermarked_base64 = self.watermark_engine.create_watermarked_document_image(
            title=doc_entry["title"],
            classification=doc_entry["classification"],
            text_content=decrypted_text,
            wid_hex=w_id
        )

        sm.transition_to(PipelineStage.WATERMARKED, f"2D Haar DWT W_ID embedded ({w_id[:16]}...).")

        # Stage 6: DELIVERED
        sm.transition_to(PipelineStage.DELIVERED, "Secure viewer package assembled and ready for delivery.")

        # Update lockbox state in memory and SQLite
        lockbox["status"] = "decrypted"
        for r in doc_entry["recipients"]:
            if r.uid == req.uid:
                r.status = "decrypted"
        self.sqlite_store.update_lockbox_status(req.doc_id, req.uid, "decrypted")

        ledger_record = {
            "ledgerId": f"LR-{commit_res['block_id']}",
            "docId": req.doc_id,
            "officerUid": req.uid,
            "sessionId": session_id,
            "receipt": m_receipt,
            "signature": sig_bytes.hex(),
            "wId": w_id,
            "y_current": y_current,
            "timestamp": time.time() * 1000,
            "status": "committed",
            "consensusNodes": commit_res.get("agreeing_nodes", ["NODE-ALPHA", "NODE-BRAVO", "NODE-CHARLIE"])
        }

        return DecryptionResponse(
            doc_id=req.doc_id,
            uid=req.uid,
            session_id=session_id,
            current_stage=PipelineStage.DELIVERED,
            w_id=w_id,
            ledger_record=ledger_record,
            decrypted_content=decrypted_text,
            watermarked_image_base64=watermarked_base64,
            pipeline_log=sm.logs
        )

    # =========================================================================
    # PHASE 10: FORENSIC AUDIT & LEAK ATTRIBUTION
    # =========================================================================
    def process_audit_request(self, req: AuditRequest) -> AuditResponse:
        """
        Processes forensic audit request. Accepts direct W_ID* hex string
        OR extracts W_ID* from uploaded leaked photograph via DWT & OpenCV deskew.
        """
        extracted_wid = req.w_id

        if not extracted_wid and req.image_base64:
            # Decode base64 image
            clean_b64 = req.image_base64.split(",")[-1]
            img_bytes = base64.b64decode(clean_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img_np is not None:
                extracted_wid = self.watermark_engine.extract_wid_from_image(img_np)
                if not extracted_wid and self._documents:
                    for doc in self._documents.values():
                        try:
                            ref_canvas = self._create_reference_canvas(
                                doc["title"],
                                doc["classification"],
                                doc.get("plaintext_body", "")
                            )
                            extracted_wid = self.watermark_engine.extract_wid_from_image(
                                img_np, reference_np=ref_canvas
                            )
                            if extracted_wid:
                                break
                        except Exception:
                            continue
            else:
                return AuditResponse(
                    attribution_status=AuditStatus.NOT_FOUND,
                    extracted_wid="",
                    message="Failed to decode image data for watermark extraction."
                )

        if not extracted_wid:
            return AuditResponse(
                attribution_status=AuditStatus.NOT_FOUND,
                extracted_wid="",
                message="No watermark ID or image provided for audit."
            )

        # Query DLT Ledger
        audit_raw = self.ledger_service.audit_wid(extracted_wid)

        status_str = audit_raw.get("attribution_status", "NOT_FOUND")
        status_enum = AuditStatus[status_str] if status_str in AuditStatus.__members__ else AuditStatus.NOT_FOUND

        sig_verified = bool(audit_raw.get("signature_verified"))

        # Enrich candidates with registered user names
        candidates_raw = audit_raw.get("candidates", [])
        enriched_candidates = []
        for cand in candidates_raw:
            c = dict(cand)
            user_entry = self.sqlite_store.get_user(c.get("officer_uid"))
            c["officer_name"] = user_entry["name"] if user_entry else f"Officer {c.get('officer_uid')}"
            enriched_candidates.append(c)

        return AuditResponse(
            attribution_status=status_enum,
            extracted_wid=extracted_wid,
            block_id=audit_raw.get("block_id"),
            client_receipt=audit_raw.get("client_receipt"),
            client_signature=audit_raw.get("client_signature"),
            y_current=audit_raw.get("y_current"),
            parsed_receipt=audit_raw.get("parsed_receipt"),
            signature_verified=sig_verified,
            message=audit_raw.get("message", "Audit query complete."),
            candidates=enriched_candidates
        )

    def _create_reference_canvas(self, title: str, classification: str, text_content: str) -> np.ndarray:
        """Renders an unwatermarked reference canvas for guided sub-pixel homography alignment."""
        from PIL import Image, ImageDraw
        from ml.embed import EMBED_W, EMBED_H
        img = Image.new("RGB", (EMBED_W, EMBED_H), color=(248, 249, 250))
        draw = ImageDraw.Draw(img)
        header_color = (
            (185, 28, 28) if classification == "RESTRICTED"
            else ((217, 119, 6) if classification == "CONFIDENTIAL"
            else (30, 41, 59))
        )
        draw.rectangle([0, 0, EMBED_W, 80], fill=header_color)
        draw.text(
            (40, 26),
            f"[{classification}] ASTRAEA QUANTUM SECURE PROVENANCE SYSTEM",
            fill=(255, 255, 255)
        )
        draw.text((50, 115), f"DOCUMENT: {title}", fill=(20, 20, 20))
        draw.line([(50, 155), (EMBED_W - 50, 155)], fill=(200, 200, 200), width=2)
        lines = text_content.split("\n")
        y_offset = 185
        for line in lines:
            draw.text((50, y_offset), line, fill=(35, 35, 35))
            y_offset += 32
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def list_documents(self) -> List[DocumentMetadataResponse]:
        """Lists all distributed document metadata."""
        res = []
        for doc in self._documents.values():
            res.append(DocumentMetadataResponse(
                doc_id=doc["doc_id"],
                title=doc["title"],
                classification=doc["classification"],
                ciphertext_fp=doc["ciphertext_fp"],
                created_at=doc["created_at"],
                recipients=doc["recipients"]
            ))
        return res

    def get_document_by_id(self, doc_id: str) -> Optional[DocumentMetadataResponse]:
        """Retrieves single document metadata."""
        doc = self._documents.get(doc_id)
        if not doc:
            return None
        return DocumentMetadataResponse(
            doc_id=doc["doc_id"],
            title=doc["title"],
            classification=doc["classification"],
            ciphertext_fp=doc["ciphertext_fp"],
            created_at=doc["created_at"],
            recipients=doc["recipients"]
        )
