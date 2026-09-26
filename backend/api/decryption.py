from fastapi import APIRouter, HTTPException, Depends
from backend.models.requests import DecryptionRequest
from backend.models.responses import DecryptionResponse
from backend.services import ASTRAEAPipelineService

router = APIRouter(tags=["Decryption & Key Release"])

def get_pipeline_service() -> ASTRAEAPipelineService:
    from backend.main import pipeline_service
    return pipeline_service

@router.post("/request_decryption", response_model=DecryptionResponse)
@router.post("/api/v1/request_decryption", response_model=DecryptionResponse, include_in_schema=False)
async def request_decryption(
    req: DecryptionRequest,
    pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)
):
    """
    POST /request_decryption
    Input: UID, DocID, Timestamp, ML-DSA signature over m_receipt.
    Process: Dynamic state transitions -> ML-DSA verification -> DLT 3-node consensus -> Ledger commit -> Key Release -> DWT watermark.
    """
    try:
        return await pipeline.process_decryption_request(req)
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except RuntimeError as rt_err:
        raise HTTPException(status_code=422, detail=str(rt_err))
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(ex)}")
