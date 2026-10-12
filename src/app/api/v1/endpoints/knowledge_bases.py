from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.tenant_db import get_tenant_database_url, get_tenant_db
from app.repositories.knowledge_bases_repository import (
    NothingToPublishError,
    create_knowledge_base as repo_create_knowledge_base,
    list_knowledge_bases,
    mark_golden_dataset_pending,
    publish_knowledge_base as repo_publish_knowledge_base,
    soft_delete_knowledge_base,
    update_knowledge_base as repo_update_knowledge_base,
)
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.services.golden_dataset_service import regenerate_golden_dataset_on_publish

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.get(
    "",
    response_model=KnowledgeBaseListResponse,
    summary="Listar knowledge bases",
    description="Retorna todas as knowledge bases cadastradas com suas configurações e metadados principais.",
    response_description="Lista de knowledge bases.",
    responses={404: {"description": "Client not found"}},
)
def list_knowledge_bases_endpoint(db: Session = Depends(get_tenant_db)) -> KnowledgeBaseListResponse:
    bases = list_knowledge_bases(db)
    return KnowledgeBaseListResponse(bases=[KnowledgeBaseRead.model_validate(item) for item in bases])


@router.post(
    "",
    response_model=KnowledgeBaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar knowledge base",
    description="Cria uma nova knowledge base, dentro do banco do cliente identificado pelo header X-Client-Slug.",
    response_description="Knowledge base criada.",
    responses={404: {"description": "Client not found"}},
)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    db: Session = Depends(get_tenant_db),
) -> KnowledgeBaseRead:
    created = repo_create_knowledge_base(
        db,
        name=payload.name,
        description=payload.description,
        kb_type=payload.type,
    )
    return KnowledgeBaseRead.model_validate(created)


@router.patch(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead,
    summary="Atualizar knowledge base",
    description="Atualiza parcialmente os campos informados de uma knowledge base existente.",
    response_description="Knowledge base atualizada.",
    responses={404: {"description": "Knowledge base not found"}},
)
def update_knowledge_base(
    knowledge_base_id: UUID,
    payload: KnowledgeBaseUpdate,
    db: Session = Depends(get_tenant_db),
) -> KnowledgeBaseRead:
    updated = repo_update_knowledge_base(
        db,
        knowledge_base_id=knowledge_base_id,
        update_data=payload.model_dump(exclude_unset=True),
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    return KnowledgeBaseRead.model_validate(updated)


@router.post(
    "/{knowledge_base_id}/publish",
    response_model=KnowledgeBaseRead,
    summary="Publicar knowledge base",
    description=(
        "Promove o conteúdo em edição (documentos e relatórios EDIT) para produção (PUBLISHED), "
        "sobrescrevendo definitivamente o conteúdo PUBLISHED anterior. O conteúdo em edição já é "
        "consultável via /rag-chat antes mesmo de publicar. Dispara em background a regeneração do "
        "golden dataset a partir do relatório recém-publicado (substitui qualquer golden question "
        "anterior, gerada ou manual, pois ela refletia a versão publicada anterior), para a aba "
        "Avaliação já vir com o que precisa para rodar."
    ),
    response_description="Knowledge base publicada.",
    responses={
        404: {"description": "Knowledge base not found"},
        409: {"description": "Knowledge base has no pending changes to publish"},
    },
)
def publish_knowledge_base(
    knowledge_base_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_tenant_db),
    database_url: str = Depends(get_tenant_database_url),
) -> KnowledgeBaseRead:
    try:
        published = repo_publish_knowledge_base(db, knowledge_base_id=knowledge_base_id)
    except NothingToPublishError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Knowledge base has no pending changes to publish",
        )
    if published is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    # Marca PENDING já na resposta deste request (antes de agendar o background task, que só
    # confirma esse mesmo status via sua própria sessão) para o frontend poder pollar
    # golden_dataset_status a partir do retorno deste POST, sem uma corrida de "ainda está IDLE".
    mark_golden_dataset_pending(db, knowledge_base_id=knowledge_base_id)
    published["golden_dataset_status"] = "PENDING"
    published["golden_dataset_error_message"] = None

    background_tasks.add_task(
        regenerate_golden_dataset_on_publish, database_url, knowledge_base_id=knowledge_base_id
    )

    return KnowledgeBaseRead.model_validate(published)


@router.delete(
    "/{knowledge_base_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover knowledge base",
    description="Remove (soft delete) uma knowledge base existente, marcando-a como excluída sem apagar os dados.",
    responses={404: {"description": "Knowledge base not found"}},
)
def delete_knowledge_base(
    knowledge_base_id: UUID,
    db: Session = Depends(get_tenant_db),
) -> None:
    deleted = soft_delete_knowledge_base(db, knowledge_base_id=knowledge_base_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
