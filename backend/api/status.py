from fastapi import APIRouter, Depends
from typing import Dict, Any
from backend.models.responses import SystemStatusResponse
from backend.services import ASTRAEAPipelineService
from backend.crypto_interface.wrapper import OQS_SUPPORTED

router = APIRouter(tags=["System Status"])

def get_pipeline_service() -> ASTRAEAPipelineService:
    from backend.main import pipeline_service
    return pipeline_service

@router.get("/status", response_model=SystemStatusResponse)
@router.get("/api/v1/status", response_model=SystemStatusResponse, include_in_schema=False)
async def get_system_status(pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)):
    """GET /status - Overall system health, connected modules and cryptographic provider state."""
    ledger_status = pipeline.ledger_service.get_ledger_status()
    crypto_status = {
        "provider": "liboqs (NIST FIPS 203/204)" if OQS_SUPPORTED else "Post-Quantum Simulator (Development Mode)",
        "kem_algo": "ML-KEM-768",
        "dsa_algo": "ML-DSA-65",
        "symmetric_algo": "AES-256-GCM",
        "hash_chain_algo": "Monotonic Feistel Hash-Chain (MFHC) + BLAKE3",
        "watermark_algo": "2D Haar DWT + Reed-Solomon FEC"
    }

    return SystemStatusResponse(
        app_name="ASTRAEA API & Data Flow Backend",
        status="ONLINE",
        version="1.0.0",
        ledger_status=ledger_status,
        crypto_status=crypto_status
    )

@router.get("/ledger/status")
@router.get("/api/v1/ledger/status", include_in_schema=False)
async def get_ledger_status(pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)) -> Dict[str, Any]:
    """GET /ledger/status - Returns DLT 3-node consensus cluster height, hashes, and integrity status."""
    return pipeline.ledger_service.get_ledger_status()
