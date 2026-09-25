import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from ledger.config import LedgerConfig
from ledger.engine import LedgerEngine
from ledger.models import (
    BlockRecord,
    BlockCommitRequest,
    BlockCommitResponse,
    BlockTraversalResponse,
    ChainIntegrityReport,
    ForensicAuditRequest,
    ForensicAuditResponse,
    NodeStatusResponse,
)

logger = logging.getLogger("ASTRAEA.LedgerAPI")

def create_ledger_app(config: Optional[LedgerConfig] = None) -> FastAPI:
    """Factory function to instantiate an ASTRAEA Ledger Node FastAPI service."""
    cfg = config or LedgerConfig.from_env()
    engine = LedgerEngine(cfg)

    app = FastAPI(
        title=f"ASTRAEA MFHC Ledger Node [{cfg.node_id}]",
        description="Tamper-evident Monotonic Feistel Hash-Chain provenance ledger for Project ASTRAEA",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/ledger/status", response_model=NodeStatusResponse, tags=["Health"])
    def get_status():
        """Returns health status, head block height, and committed hash of this node."""
        try:
            return engine.get_status()
        except Exception as e:
            logger.error(f"Failed to fetch status: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # =========================================================================
    # OUTCOME 1: Request to Add a Block
    # =========================================================================
    @app.post(
        "/ledger/commit",
        response_model=BlockCommitResponse,
        status_code=status.HTTP_200_OK,
        tags=["Commit"]
    )
    def commit_block(request: BlockCommitRequest):
        """
        Request to add a block to the ledger.
        
        Validates the client ML-DSA signature over the decryption intent receipt,
        advances the MFHC state via the monotonic Feistel transform,
        commits the block to the append-only ledger, and derives the W_ID watermark identifier.
        """
        try:
            response = engine.commit_block(
                client_receipt=request.client_receipt,
                client_signature=request.client_signature,
                recipient_public_key=request.recipient_public_key,
                metadata=request.metadata
            )
            return response
        except ValueError as ve:
            logger.warning(f"Block committal rejected: {ve}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(ve)
            )
        except Exception as e:
            logger.error(f"Unexpected error committing block: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ledger commit failed: {str(e)}"
            )

    # =========================================================================
    # OUTCOME 2: Traverse the Ledger Blocks
    # =========================================================================
    @app.get(
        "/ledger/blocks",
        response_model=BlockTraversalResponse,
        tags=["Traversal"]
    )
    def traverse_blocks(
        offset: int = Query(0, ge=0, description="Pagination start offset"),
        limit: Optional[int] = Query(None, ge=1, le=1000, description="Max blocks to return"),
        reverse: bool = Query(False, description="If True, returns Head -> Genesis; if False, returns Genesis -> Head")
    ):
        """
        Traverse the ledger blocks in sequential order.
        Allows auditing the entire chain progression from Genesis to Head or reverse.
        """
        try:
            return engine.traverse_blocks(offset=offset, limit=limit, reverse=reverse)
        except Exception as e:
            logger.error(f"Failed to traverse blocks: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    @app.get(
        "/ledger/blocks/{block_id}",
        response_model=BlockRecord,
        tags=["Traversal"]
    )
    def get_block_by_id(block_id: int):
        """Retrieve a specific block by its sequence index."""
        block = engine.get_block_by_id(block_id)
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Block with ID #{block_id} not found in ledger."
            )
        return block

    @app.get(
        "/ledger/blocks/hash/{y_hash}",
        response_model=BlockRecord,
        tags=["Traversal"]
    )
    def get_block_by_hash(y_hash: str):
        """Retrieve a specific block by its committed state hash y_current."""
        block = engine.get_block_by_hash(y_hash)
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Block with hash '{y_hash}' not found in ledger."
            )
        return block

    # =========================================================================
    # Cryptographic Chain Integrity Verification
    # =========================================================================
    @app.get(
        "/ledger/verify",
        response_model=ChainIntegrityReport,
        tags=["Audit & Integrity"]
    )
    def verify_integrity():
        """
        Audits and traverses the entire hash-chain, recomputing all Feistel masks
        and BLAKE3 state transitions to mathematically prove tamper-evidence.
        """
        try:
            return engine.verify_chain_integrity()
        except Exception as e:
            logger.error(f"Integrity check failed: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # =========================================================================
    # Forensic Audit: Leak Attribution by Watermark ID
    # =========================================================================
    @app.post(
        "/ledger/audit",
        response_model=ForensicAuditResponse,
        tags=["Audit & Integrity"]
    )
    def audit_watermark(request: ForensicAuditRequest):
        """
        Forensic lookup: traverses blocks to attribute an analog-recovered watermark ID
        to the exact officer, document, and decryption session.
        """
        try:
            return engine.audit_forensic_wid(request.extracted_wid)
        except Exception as e:
            logger.error(f"Forensic audit failed: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return app

# Default ASGI application instance for uvicorn
app = create_ledger_app()
