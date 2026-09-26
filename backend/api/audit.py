from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional
import base64

from backend.models.requests import AuditRequest
from backend.models.responses import AuditResponse
from backend.services import ASTRAEAPipelineService

router = APIRouter(tags=["Forensic Audit"])

def get_pipeline_service() -> ASTRAEAPipelineService:
    from backend.main import pipeline_service
    return pipeline_service

@router.post("/audit", response_model=AuditResponse)
@router.post("/api/v1/audit", response_model=AuditResponse, include_in_schema=False)
async def audit_forensic_id(
    req: AuditRequest,
    pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)
):
    """
    POST /audit (JSON payload)
    Input: W_ID* hex string or base64 image string.
    Process: Extracts W_ID*, searches DLT ledger, verifies ML-DSA signature provenance.
    Returns: FOUND, FOUND_BUT_INVALID, or NOT_FOUND.
    """
    try:
        return pipeline.process_audit_request(req)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))

@router.post("/audit/upload", response_model=AuditResponse)
async def audit_uploaded_image(
    file: UploadFile = File(...),
    pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)
):
    """
    POST /audit/upload (Form File upload)
    Input: Leaked image file (PNG/JPEG/BMP).
    Process: Extracts W_ID* using OpenCV deskew + DWT extraction, performs DLT lookup & verification.
    """
    try:
        content = await file.read()
        b64_str = base64.b64encode(content).decode("utf-8")
        req = AuditRequest(image_base64=b64_str)
        return pipeline.process_audit_request(req)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Image upload audit failed: {str(ex)}")
