from fastapi import APIRouter
from backend.api.broadcast import router as broadcast_router
from backend.api.decryption import router as decryption_router
from backend.api.audit import router as audit_router
from backend.api.document import router as document_router
from backend.api.status import router as status_router
from backend.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(broadcast_router)
api_router.include_router(decryption_router)
api_router.include_router(audit_router)
api_router.include_router(document_router)
api_router.include_router(status_router)
api_router.include_router(users_router)

__all__ = ["api_router"]
