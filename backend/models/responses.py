from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.models.state import PipelineStage, AuditStatus

class RecipientLockbox(BaseModel):
    uid: str
    name: Optional[str] = None
    lockbox_ref: str
    c_u_hex: Optional[str] = None
    status: str = "delivered"

class BroadcastResponse(BaseModel):
    doc_id: str
    title: str
    classification: str
    ciphertext_fp: str
    created_at: float
    recipients: List[RecipientLockbox]
    message: str = "Document encrypted with AES-256-GCM and lockboxes created via ML-KEM."

class PipelineStepLog(BaseModel):
    stage: PipelineStage
    status: str
    timestamp: float
    detail: Optional[str] = None

class DecryptionResponse(BaseModel):
    doc_id: str
    uid: str
    session_id: str
    current_stage: PipelineStage
    w_id: str
    ledger_record: Dict[str, Any]
    decrypted_content: str
    watermarked_image_base64: Optional[str] = None
    pipeline_log: List[PipelineStepLog]
    message: str = "Key released after DLT consensus & watermark embedded."

class AuditResponse(BaseModel):
    attribution_status: AuditStatus
    extracted_wid: str
    block_id: Optional[int] = None
    client_receipt: Optional[str] = None
    client_signature: Optional[str] = None
    y_current: Optional[str] = None
    parsed_receipt: Optional[Dict[str, str]] = None
    signature_verified: bool = False
    message: str
    candidates: Optional[List[Dict[str, Any]]] = None

class DocumentMetadataResponse(BaseModel):
    doc_id: str
    title: str
    classification: str
    ciphertext_fp: str
    created_at: float
    recipients: List[RecipientLockbox]

class SystemStatusResponse(BaseModel):
    app_name: str
    status: str = "ONLINE"
    version: str = "1.0.0"
    ledger_status: Dict[str, Any]
    crypto_status: Dict[str, Any]
