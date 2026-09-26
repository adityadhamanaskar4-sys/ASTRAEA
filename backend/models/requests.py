from typing import List, Optional
from pydantic import BaseModel, Field

class BroadcastRequest(BaseModel):
    title: str = Field(..., description="Document title")
    classification: str = Field("RESTRICTED", description="Classification level (e.g., RESTRICTED, CONFIDENTIAL)")
    body: str = Field(..., description="Plaintext document body content or base64 string")
    recipient_uids: List[str] = Field(..., description="List of recipient UIDs authorized to receive lockboxes")

class DecryptionRequest(BaseModel):
    uid: str = Field(..., description="Recipient officer UID (e.g., OFC-2291)")
    doc_id: str = Field(..., description="Document identifier (e.g., DOC-8819)")
    timestamp: str = Field(..., description="ISO 8601 timestamp string of decryption request")
    signature: str = Field(..., description="ML-DSA signature over m_receipt = UID || DocID || Timestamp")
    recipient_pk: Optional[str] = Field(None, description="Recipient ML-DSA public key in hex (optional)")

class AuditRequest(BaseModel):
    w_id: Optional[str] = Field(None, description="256-bit hex Watermark ID (W_ID*)")
    image_base64: Optional[str] = Field(None, description="Base64 encoded leaked image string")
