from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    summary="Checar saúde do serviço",
    description="Retorna o estado atual da aplicação para monitoramento e readiness checks.",
    response_description="Status de saúde do serviço.",
)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
