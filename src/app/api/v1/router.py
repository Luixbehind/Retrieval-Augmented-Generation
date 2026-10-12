from fastapi import APIRouter

from app.api.v1.endpoints.clients import router as clients_router
from app.api.v1.endpoints.evaluations import router as evaluations_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.knowledge_bases import router as knowledge_bases_router
from app.api.v1.endpoints.lgpd_compliance import router as lgpd_compliance_router
from app.api.v1.endpoints.rag_chat import router as rag_chat_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(clients_router, tags=["clients"])
api_router.include_router(knowledge_bases_router, tags=["knowledge-bases"])
api_router.include_router(lgpd_compliance_router, tags=["lgpd-compliance"])
api_router.include_router(rag_chat_router, tags=["rag-chat"])
api_router.include_router(evaluations_router, tags=["evaluations"])
