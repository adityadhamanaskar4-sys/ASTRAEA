import logging
from typing import Dict, Any, Optional

from ledger.engine import LedgerEngine
from ledger.consensus import ConsensusCoordinator
from ledger.config import LedgerConfig

logger = logging.getLogger("ASTRAEA.LedgerService")


class LedgerService:
    """
    Bridge connecting Backend 1 (API & Data Flow) to Backend 2 (DLT Ledger & Consensus).
    Enforces DLT commitment and 3-node consensus before decryption keys are released.
    """

    def __init__(self, db_path: str = "astraea_ledger.db"):
        self.primary_engine = LedgerEngine(LedgerConfig(db_path=db_path, node_id="NODE-ALPHA"))
        # Initialize 3-node consensus simulation coordinator
        self.consensus_cluster = ConsensusCoordinator.create_in_memory_or_local_cluster("data/cluster")

    async def commit_decryption_receipt(
        self,
        receipt_str: str,
        signature: bytes | str,
        recipient_pk: Optional[bytes | str] = None
    ) -> Dict[str, Any]:
        """
        Commits decryption receipt to 3-node consensus cluster.
        Returns consensus commit result including authorization_granted flag, y_current hash, and W_ID.
        """
        # Execute 3-node consortium consensus simulation
        consensus_res = await self.consensus_cluster.commit_distributed(
            client_receipt=receipt_str,
            client_signature=signature,
            recipient_public_key=recipient_pk
        )
        
        # Also ensure primary engine records the block
        primary_res = self.primary_engine.commit_block(
            client_receipt=receipt_str,
            client_signature=signature,
            recipient_public_key=recipient_pk
        )

        return {
            "consensus_achieved": consensus_res.consensus_achieved,
            "quorum_fraction": consensus_res.quorum_fraction,
            "authorization_granted": consensus_res.authorization_granted,
            "y_current": primary_res.y_current,
            "w_id": primary_res.w_id,
            "block_id": primary_res.block_id,
            "agreeing_nodes": consensus_res.agreeing_nodes,
            "message": consensus_res.message
        }

    def audit_wid(self, extracted_wid: str, doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Looks up a 256-bit watermark ID (W_ID*) across ledger database nodes, optionally scoped by doc_id."""
        audit_res = self.primary_engine.audit_forensic_wid(extracted_wid, doc_id=doc_id)
        if audit_res.attribution_status == "FOUND":
            return audit_res.model_dump()
        for engine in self.consensus_cluster.engines:
            cluster_audit = engine.audit_forensic_wid(extracted_wid, doc_id=doc_id)
            if cluster_audit.attribution_status == "FOUND":
                return cluster_audit.model_dump()
        return audit_res.model_dump()

    def get_ledger_status(self) -> Dict[str, Any]:
        """Returns primary node and cluster status."""
        status = self.primary_engine.get_status().model_dump()
        status["cluster_integrity"] = self.consensus_cluster.check_all_nodes_integrity()
        return status
