import sys
from pathlib import Path

# Ensure project root directory is on sys.path whether executed from root or backend/
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.config import config
from backend.services import ASTRAEAPipelineService
from backend.api import api_router
from backend.models.requests import BroadcastRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ASTRAEA.Main")

# Global pipeline service instance
pipeline_service = ASTRAEAPipelineService(db_path=config.ledger_db_path)

def seed_sample_data(service: ASTRAEAPipelineService):
    """Seeds initial demonstration documents into Backend 1."""
    try:
        if len(service.list_documents()) == 0:
            doc1 = BroadcastRequest(
                title="OP ORDER — ALPHA",
                classification="RESTRICTED",
                body="Section 4.2 — Movement Schedule\nSector clearance pending final authorization from command.",
                recipient_uids=["OFC-2291", "OFC-1187", "OFC-3305"]
            )
            doc2 = BroadcastRequest(
                title="SATCOM FREQUENCY TABLE",
                classification="CONFIDENTIAL",
                body="Channel allocation — Q3 rotation\nPrimary / secondary uplink pairs listed by sector code.",
                recipient_uids=["OFC-2291", "OFC-1187"]
            )
            service.broadcast_document(doc1)
            service.broadcast_document(doc2)
            logger.info("Sample demonstration documents seeded into Backend 1 API service.")
    except Exception as ex:
        logger.warning(f"Demo seeding skipped: {ex}")

def create_app() -> FastAPI:
    app = FastAPI(
        title=config.app_name,
        description="Project ASTRAEA Backend 1 — API & Data Flow System connecting Frontend, Cryptography, DLT, Watermarking & Forensic Audit.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Enable CORS for Frontend (Vite / React / local web UI)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all API routes
    app.include_router(api_router)

    @app.on_event("startup")
    async def startup_event():
        logger.info(f"Starting {config.app_name} on {config.host}:{config.port}")
        seed_sample_data(pipeline_service)

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=config.host, port=config.port, reload=True)
