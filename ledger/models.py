from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class BlockRecord(BaseModel):
    """Represents a single immutable row in the Monotonic Feistel Hash-Chain."""
    block_id: int = Field(..., description="Unique auto-incrementing block index")
    timestamp: str = Field(..., description="ISO/SQLite committal timestamp")
    y_prev: str = Field(..., description="Hex hash of the preceding block (64 chars)")
    mask: str = Field(..., description="Feistel chain mask M_chain generated for this block (64 chars)")
    client_signature: str = Field(..., description="Hex-encoded client ML-DSA signature")
    client_receipt: str = Field(..., description="Decryption intent receipt string (UID || DocID || Timestamp)")
    y_current: str = Field(..., description="Committed state hash y_i of this block (64 chars)")

class BlockCommitRequest(BaseModel):
    """Request payload to commit a new block to the ledger."""
    client_receipt: str = Field(..., min_length=1, description="Decryption intent receipt: UID || DocID || Timestamp")
    client_signature: str = Field(..., min_length=1, description="Hex or base64 encoded client signature")
    recipient_public_key: Optional[str] = Field(None, description="Optional hex/base64 ML-DSA public key for signature verification")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional extra audit metadata")

class BlockCommitResponse(BaseModel):
    """Response returned upon successful block committal to the MFHC ledger."""
    status: str = Field("authorized", description="Authorization status (authorized/rejected)")
    node_id: str = Field(..., description="Identifier of the committing node")
    block_id: int = Field(..., description="Assigned block index")
    timestamp: str = Field(..., description="Committal timestamp")
    y_prev: str = Field(..., description="Preceding block hash")
    mask: str = Field(..., description="Generated Feistel mask")
    y_current: str = Field(..., description="Committed block state y_i")
    w_id: str = Field(..., description="Derived 256-bit steganographic watermark identifier (64 hex characters)")
    message: str = Field("Block committed successfully to MFHC ledger", description="Status description")

class BlockTraversalResponse(BaseModel):
    """Paginated response containing traversed blocks from the ledger."""
    total_blocks: int = Field(..., description="Total blocks currently in the ledger")
    offset: int = Field(0, description="Offset used for pagination")
    limit: Optional[int] = Field(None, description="Maximum blocks returned in this page")
    order: str = Field("asc", description="Traversal order: 'asc' (Genesis to Head) or 'desc' (Head to Genesis)")
    blocks: List[BlockRecord] = Field(default_factory=list, description="Traversed block records")

class ChainIntegrityReport(BaseModel):
    """Report detailing the mathematical integrity of the Monotonic Feistel Hash-Chain."""
    is_valid: bool = Field(..., description="True if every block mathematically links to its predecessor")
    total_blocks: int = Field(..., description="Total blocks audited in the chain")
    head_hash: Optional[str] = Field(None, description="Committed hash of the current head block")
    genesis_hash: Optional[str] = Field(None, description="Hash of the genesis block")
    broken_at_block_id: Optional[int] = Field(None, description="First block ID where tampering was detected")
    error_reason: Optional[str] = Field(None, description="Explanation of cryptographic mismatch")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Diagnostic data")

class ForensicAuditRequest(BaseModel):
    """Request payload to query the ledger using an extracted watermark ID."""
    extracted_wid: str = Field(..., min_length=1, description="Hex watermark or fragment recovered from leak")
    doc_id: Optional[str] = Field(None, description="Optional document ID to narrow search window")

class ForensicAuditResponse(BaseModel):
    """Cryptographic attribution response for a forensic leak investigation."""
    attribution_status: str = Field(..., description="'FOUND', 'PARTIAL_MATCH', 'FOUND_BUT_INVALID', or 'NOT_FOUND'")
    extracted_wid: str = Field(..., description="Watermark ID searched")
    block_id: Optional[int] = Field(None, description="Block index where top match was found")
    client_receipt: Optional[str] = Field(None, description="Attributed intent receipt (UID || DocID || Timestamp)")
    client_signature: Optional[str] = Field(None, description="Hex signature attached to the receipt")
    y_current: Optional[str] = Field(None, description="Committed ledger state at the time of decryption")
    parsed_receipt: Optional[Dict[str, str]] = Field(default_factory=dict, description="Parsed UID, DocID, Timestamp")
    signature_verified: Optional[bool] = Field(None, description="Whether ML-DSA signature verification succeeded")
    message: str = Field(..., description="Summary of attribution finding")
    candidates: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Ranked list of candidate officers matching or similar to W_ID*")

class NodeStatusResponse(BaseModel):
    """Status and health of the local DLT node."""
    node_id: str
    head_block_id: int
    head_hash: str
    genesis_hash: str
    total_blocks: int
    status: str = "ONLINE"
