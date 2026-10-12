from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

openapi_tags = [
    {"name": "root", "description": "Endpoints de verificação básica da API."},
    {"name": "health", "description": "Checagem de saúde do serviço."},
    {
        "name": "clients",
        "description": "Provisionamento e gestão de clientes/tenants, cada um com seu próprio banco isolado.",
    },
    {"name": "knowledge-bases", "description": "Criação, listagem e atualização de knowledge bases."},
    {
        "name": "knowledge-documents",
        "description": "Upload, listagem, consulta de status e remoção lógica de documentos de knowledge base.",
    },
    {
        "name": "lgpd-compliance",
        "description": "Análise de conformidade LGPD e exportação de relatórios persistidos.",
    },
    {"name": "queries", "description": "Consulta RAG híbrida para LGPD e knowledge bases de cliente."},
]

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API para RAG, gestão de knowledge bases, processamento de documentos e análise de conformidade LGPD.",
    openapi_tags=openapi_tags,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get(
    "/",
    tags=["root"],
    summary="Verificar disponibilidade da API",
    description="Retorna uma mensagem simples para confirmar que o serviço está ativo.",
    response_description="Mensagem de status da API.",
)
async def root() -> dict[str, str]:
    return {"message": "RAG API is running"}


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
