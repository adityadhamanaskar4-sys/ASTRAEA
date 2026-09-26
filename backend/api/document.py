from fastapi import APIRouter, HTTPException, Depends
from typing import List
from backend.models.responses import DocumentMetadataResponse
from backend.services import ASTRAEAPipelineService

router = APIRouter(tags=["Document Management"])

def get_pipeline_service() -> ASTRAEAPipelineService:
    from backend.main import pipeline_service
    return pipeline_service

@router.get("/documents", response_model=List[DocumentMetadataResponse])
@router.get("/api/v1/documents", response_model=List[DocumentMetadataResponse], include_in_schema=False)
async def list_all_documents(pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)):
    """GET /documents - List metadata for all distributed documents."""
    return pipeline.list_documents()

@router.get("/document/{doc_id}", response_model=DocumentMetadataResponse)
@router.get("/api/v1/document/{doc_id}", response_model=DocumentMetadataResponse, include_in_schema=False)
async def get_document_by_id(
    doc_id: str,
    pipeline: ASTRAEAPipelineService = Depends(get_pipeline_service)
):
    """GET /document/{doc_id} - Fetch single document metadata and lockbox status."""
    doc = pipeline.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")
    return doc
