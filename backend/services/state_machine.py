import logging
import time
from typing import List
from backend.models.state import PipelineStage
from backend.models.responses import PipelineStepLog

logger = logging.getLogger("ASTRAEA.StateMachine")

# Allowed sequential transitions
TRANSITION_ORDER = [
    PipelineStage.REQUESTED,
    PipelineStage.SIGNATURE_VERIFIED,
    PipelineStage.LEDGER_PENDING,
    PipelineStage.LEDGER_COMMITTED,
    PipelineStage.TOKEN_RELEASED,
    PipelineStage.DECRYPTED,
    PipelineStage.WATERMARKED,
    PipelineStage.DELIVERED,
]


class PipelineStateMachine:
    """
    Enforces strict sequential state transitions for Project ASTRAEA data flow pipeline.
    
    Rule (per ASTRAEA_Backend(1+2).md line 133-137):
    If any critical step fails -> STOP. Do not silently continue.
    Key release condition: VALID SIGNATURE + VALID LEDGER PROCESSING + SUCCESSFUL COMMIT.
    """

    def __init__(self, doc_id: str, uid: str, session_id: str):
        self.doc_id = doc_id
        self.uid = uid
        self.session_id = session_id
        self.current_stage = PipelineStage.REQUESTED
        self.logs: List[PipelineStepLog] = []

    def transition_to(self, target_stage: PipelineStage, detail: str = "") -> PipelineStepLog:
        """Transitions to the target stage if valid, appending to pipeline step log."""
        if self.current_stage == PipelineStage.FAILED:
            raise RuntimeError(f"Cannot transition from FAILED stage to {target_stage}.")

        curr_idx = TRANSITION_ORDER.index(self.current_stage) if self.current_stage in TRANSITION_ORDER else -1
        target_idx = TRANSITION_ORDER.index(target_stage) if target_stage in TRANSITION_ORDER else -1

        # Strict ordering check
        if target_idx != curr_idx + 1:
            err_msg = f"Invalid transition sequence: {self.current_stage} -> {target_stage}. Step order violated."
            self.fail(err_msg)
            raise ValueError(err_msg)

        self.current_stage = target_stage
        log_entry = PipelineStepLog(
            stage=target_stage,
            status="SUCCESS",
            timestamp=time.time(),
            detail=detail
        )
        self.logs.append(log_entry)
        logger.info(f"[{self.doc_id}:{self.uid}] Transition -> {target_stage}: {detail}")
        return log_entry

    def fail(self, error_message: str):
        """Halts the pipeline immediately in FAILED state."""
        self.current_stage = PipelineStage.FAILED
        log_entry = PipelineStepLog(
            stage=PipelineStage.FAILED,
            status="FAILED",
            timestamp=time.time(),
            detail=error_message
        )
        self.logs.append(log_entry)
        logger.error(f"[{self.doc_id}:{self.uid}] PIPELINE FAILED: {error_message}")
        return log_entry
