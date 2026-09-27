from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.services import ASTRAEAPipelineService
from backend.crypto_interface import CryptoWrapper

router = APIRouter(tags=["User & Officer Management"])

class UserInfoResponse(BaseModel):
    uid: str
    name: str
    role: str
    clearance_level: str
    pk_dsa_hex: Optional[str] = None
    created_at: Optional[str] = None

class SignReceiptRequest(BaseModel):
    receipt: Optional[str] = Field(None, description="Formatted receipt string: UID || DocID || Timestamp")
    doc_id: Optional[str] = Field(None, description="Document ID if receipt string not formatted")
    timestamp: Optional[str] = Field(None, description="Timestamp string")

class SignReceiptResponse(BaseModel):
    uid: str
    receipt: str
    signature: str
    recipient_pk: str

def get_pipeline_service() -> ASTRAEAPipelineService:
    from backend.main import pipeline_service
    return pipeline_service

@router.get("/users", response_model=List[UserInfoResponse])
@router.get("/api/v1/users", response_model=List[UserInfoResponse], include_in_schema=False)
async def list_users(pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)):
    """GET /users - Lists all defense personnel and intelligence officers from SQLite database."""
    return pipeline.list_users()

@router.get("/users/{uid}", response_model=UserInfoResponse)
@router.get("/api/v1/users/{uid}", response_model=UserInfoResponse, include_in_schema=False)
async def get_user_profile(uid: str, pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)):
    """GET /users/{uid} - Fetches officer profile by UID from SQLite."""
    user = pipeline.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {uid} not found in SQLite registry.")
    return user

@router.post("/users/{uid}/sign", response_model=SignReceiptResponse)
@router.post("/api/v1/users/{uid}/sign", response_model=SignReceiptResponse, include_in_schema=False)
async def sign_receipt_with_officer_token(
    uid: str,
    req: SignReceiptRequest,
    pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)
):
    """
    POST /users/{uid}/sign - Simulates Officer Hardware Cryptographic Token in air-gapped terminal.
    Signs receipt with user's post-quantum ML-DSA-65 secret key retrieved from SQLite.
    """
    keys = pipeline.get_user_keys(uid)
    if not keys:
        raise HTTPException(status_code=404, detail=f"Officer {uid} cryptographic key material not found.")

    m_receipt = req.receipt
    if not m_receipt:
        if not req.doc_id or not req.timestamp:
            raise HTTPException(status_code=400, detail="Must provide either 'receipt' string or ('doc_id' and 'timestamp').")
        m_receipt = f"{uid} || {req.doc_id} || {req.timestamp}"

    sig_bytes = CryptoWrapper.sign_receipt(keys["sk_dsa"], m_receipt)

    return SignReceiptResponse(
        uid=uid,
        receipt=m_receipt,
        signature=sig_bytes.hex(),
        recipient_pk=keys["pk_dsa"].hex()
    )
