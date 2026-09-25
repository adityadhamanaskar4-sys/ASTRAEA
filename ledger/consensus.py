import asyncio
import logging
from typing import List, Dict, Any, Optional
from collections import Counter
from pydantic import BaseModel, Field

from ledger.engine import LedgerEngine
from ledger.config import LedgerConfig
from ledger.models import BlockCommitResponse

logger = logging.getLogger("ASTRAEA.Consensus")

class NodeCommitVote(BaseModel):
    node_id: str
    y_current: Optional[str] = None
    w_id: Optional[str] = None
    block_id: Optional[int] = None
    success: bool
    error_message: Optional[str] = None

class ConsensusCommitResult(BaseModel):
    """Result of the 3-node consortium consensus voting."""
    consensus_achieved: bool = Field(..., description="True if at least 2 of 3 nodes agree on y_i")
    quorum_fraction: str = Field(..., description="e.g. '3/3' or '2/3'")
    agreed_hash: Optional[str] = Field(None, description="The agreed y_i block state hash")
    agreed_wid: Optional[str] = Field(None, description="The agreed forensic watermark ID")
    participating_nodes: int = Field(..., description="Number of nodes that participated")
    agreeing_nodes: List[str] = Field(default_factory=list, description="List of node IDs that agreed on y_i")
    node_votes: List[NodeCommitVote] = Field(default_factory=list, description="Individual node outcomes")
    authorization_granted: bool = Field(..., description="Whether decryption key release is authorized")
    message: str = Field(..., description="Human-readable consensus summary")


class ConsensusCoordinator:
    """
    Coordinates decentralized block commitment across 3 local ASTRAEA DLT nodes.
    Simulates the permissioned consortium network required by SIH26237 and Ministry of Defence specifications.
    
    Supports:
    1. In-process multi-engine coordination (3 distinct SQLite databases).
    2. HTTP-based broadcast across independent containerized microservices.
    """

    def __init__(self, engines: Optional[List[LedgerEngine]] = None, peer_urls: Optional[List[str]] = None):
        self.engines = engines or []
        self.peer_urls = peer_urls or []

    @classmethod
    def create_in_memory_or_local_cluster(cls, base_dir: str = "data/cluster") -> "ConsensusCoordinator":
        """Factory creating a 3-node in-process cluster with isolated SQLite databases."""
        engines = []
        for i in (1, 2, 3):
            cfg = LedgerConfig(
                node_id=f"node_{i}",
                db_path=f"{base_dir}/ledger_node_{i}.db"
            )
            engines.append(LedgerEngine(cfg))
        return cls(engines=engines)

    async def commit_distributed(
        self,
        client_receipt: str,
        client_signature: bytes | str,
        recipient_public_key: Optional[bytes | str] = None
    ) -> ConsensusCommitResult:
        """
        Broadcasts the block committal payload to all 3 nodes simultaneously.
        Enforces the rule: Key release ONLY occurs if >= 2 of 3 nodes commit the exact same y_i.
        """
        votes: List[NodeCommitVote] = []

        if self.engines:
            # In-process asynchronous dispatch
            async def _commit_to_engine(engine: LedgerEngine) -> NodeCommitVote:
                try:
                    # Run sync SQLite insert in worker thread
                    resp: BlockCommitResponse = await asyncio.to_thread(
                        engine.commit_block,
                        client_receipt,
                        client_signature,
                        recipient_public_key
                    )
                    return NodeCommitVote(
                        node_id=resp.node_id,
                        y_current=resp.y_current,
                        w_id=resp.w_id,
                        block_id=resp.block_id,
                        success=True
                    )
                except Exception as ex:
                    logger.error(f"Node {engine.config.node_id} failed commit: {ex}")
                    return NodeCommitVote(
                        node_id=engine.config.node_id,
                        success=False,
                        error_message=str(ex)
                    )

            tasks = [_commit_to_engine(e) for e in self.engines]
            votes = await asyncio.gather(*tasks)

        elif self.peer_urls:
            # Over-the-network HTTP dispatch via httpx
            import httpx

            async def _commit_to_http(url: str) -> NodeCommitVote:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        sig_str = (
                            client_signature.hex()
                            if isinstance(client_signature, bytes)
                            else client_signature
                        )
                        pk_str = (
                            recipient_public_key.hex()
                            if isinstance(recipient_public_key, bytes)
                            else recipient_public_key
                        )
                        payload = {
                            "client_receipt": client_receipt,
                            "client_signature": sig_str,
                            "recipient_public_key": pk_str
                        }
                        res = await client.post(f"{url}/ledger/commit", json=payload)
                        if res.status_code == 200:
                            data = res.json()
                            return NodeCommitVote(
                                node_id=data.get("node_id", url),
                                y_current=data["y_current"],
                                w_id=data["w_id"],
                                block_id=data["block_id"],
                                success=True
                            )
                        else:
                            return NodeCommitVote(
                                node_id=url,
                                success=False,
                                error_message=f"HTTP {res.status_code}: {res.text}"
                            )
                except Exception as ex:
                    return NodeCommitVote(
                        node_id=url,
                        success=False,
                        error_message=str(ex)
                    )

            tasks = [_commit_to_http(u) for u in self.peer_urls]
            votes = await asyncio.gather(*tasks)

        else:
            raise RuntimeError("ConsensusCoordinator has neither in-process engines nor peer URLs configured.")

        # Tally consensus votes
        valid_votes = [v for v in votes if v.success and v.y_current is not None]
        counter = Counter(v.y_current for v in valid_votes)

        if not counter:
            return ConsensusCommitResult(
                consensus_achieved=False,
                quorum_fraction="0/3",
                participating_nodes=len(votes),
                authorization_granted=False,
                node_votes=votes,
                message="Consensus failed: all nodes rejected or errored on the commit request."
            )

        modal_hash, agree_count = counter.most_common(1)[0]
        agreeing_nodes = [v.node_id for v in valid_votes if v.y_current == modal_hash]
        total_nodes = len(votes)
        quorum_fraction = f"{agree_count}/{total_nodes}"

        # Need strict majority: >= 2 out of 3
        if agree_count >= 2:
            agreed_wid = next((v.w_id for v in valid_votes if v.y_current == modal_hash), None)
            logger.info(f"Consensus SUCCESS ({quorum_fraction}) on y_i: {modal_hash[:12]}...")
            return ConsensusCommitResult(
                consensus_achieved=True,
                quorum_fraction=quorum_fraction,
                agreed_hash=modal_hash,
                agreed_wid=agreed_wid,
                participating_nodes=total_nodes,
                agreeing_nodes=agreeing_nodes,
                node_votes=votes,
                authorization_granted=True,
                message=f"Consensus achieved ({quorum_fraction}). Decryption key release authorized."
            )
        else:
            logger.warning(f"Consensus FAILED ({quorum_fraction}). Nodes split or diverged.")
            return ConsensusCommitResult(
                consensus_achieved=False,
                quorum_fraction=quorum_fraction,
                agreed_hash=modal_hash,
                participating_nodes=total_nodes,
                agreeing_nodes=agreeing_nodes,
                node_votes=votes,
                authorization_granted=False,
                message=(
                    f"Consensus failed: majority agreement not reached ({quorum_fraction}). "
                    "Decryption key release strictly blocked."
                )
            )

    def check_all_nodes_integrity(self) -> Dict[str, Any]:
        """Runs cryptographic integrity verification across all cluster nodes."""
        results = {}
        for engine in self.engines:
            results[engine.config.node_id] = engine.verify_chain_integrity().model_dump()
        return results
