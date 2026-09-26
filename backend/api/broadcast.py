from fastapi import APIRouter, HTTPException, Depends
from backend.models.requests import BroadcastRequest
from backend.models.responses import BroadcastResponse
from backend.services import ASTRAEAPipelineService

router = APIRouter(tags=["Broadcast & Encryption"])

def get_pipeline_service() -> ASTRAEAPipelineService:
    from backend.main import pipeline_service
    return pipeline_service

@router.post("/broadcast", response_model=BroadcastResponse)
@router.post("/api/v1/broadcast", response_model=BroadcastResponse, include_in_schema=False)
async def broadcast_document(
    req: BroadcastRequest,
    pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)
):
    """
    POST /broadcast
    Input: Title, Classification, Plaintext Body, Recipient UIDs.
    Process: AES-256-GCM encryption + ML-KEM lockbox encapsulation.
    """
    try:
        return pipeline.broadcast_document(req)
    except Exception as ex:
        raise HTTPException(status_code=400, detail=str(ex))
