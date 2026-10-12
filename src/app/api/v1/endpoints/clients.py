from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.control_db import get_control_db
from app.repositories.clients_repository import (
    create_client,
    get_client_by_id,
    get_client_by_slug,
    list_clients,
    soft_delete_client,
)
from app.schemas.client import ClientCreate, ClientListResponse, ClientRead
from app.services.tenant_provisioning import (
    build_tenant_db_name,
    create_tenant_database,
    run_tenant_migrations,
)

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post(
    "",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Criar cliente",
    description=(
        "Cria um novo cliente/tenant: provisiona um banco de dados Postgres isolado só para ele, aplica "
        "todas as migrations nele e registra o cliente. O par (slug, id) é a fonte da verdade para "
        "identificar o cliente em toda a API — o slug é a referência legível e estável usada no header "
        "X-Client-Slug em todas as chamadas tenant-scoped, o id é o identificador interno."
    ),
    response_description="Cliente criado.",
    responses={409: {"description": "Slug already in use"}},
)
def create_client_endpoint(
    payload: ClientCreate,
    db: Session = Depends(get_control_db),
) -> ClientRead:
    if get_client_by_slug(db, payload.slug) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    db_name = build_tenant_db_name(payload.slug)
    database_url = settings.build_database_url(db_name)

    create_tenant_database(db_name)
    run_tenant_migrations(database_url)

    created = create_client(db, slug=payload.slug, name=payload.name, db_name=db_name)
    if created is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    return ClientRead.model_validate(created)


@router.get(
    "",
    response_model=ClientListResponse,
    summary="Listar clientes",
    description="Retorna todos os clientes/tenants cadastrados.",
    response_description="Lista de clientes.",
)
def list_clients_endpoint(db: Session = Depends(get_control_db)) -> ClientListResponse:
    clients = list_clients(db)
    return ClientListResponse(clients=[ClientRead.model_validate(item) for item in clients])


@router.get(
    "/by-slug/{slug}",
    response_model=ClientRead,
    summary="Consultar cliente por slug",
    description="Retorna um cliente/tenant pelo slug — a referência legível e estável do cliente.",
    response_description="Cliente encontrado.",
    responses={404: {"description": "Client not found"}},
)
def get_client_by_slug_endpoint(
    slug: str,
    db: Session = Depends(get_control_db),
) -> ClientRead:
    client = get_client_by_slug(db, slug)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return ClientRead.model_validate(client)


@router.get(
    "/{client_id}",
    response_model=ClientRead,
    summary="Consultar cliente",
    description="Retorna um cliente/tenant pelo id.",
    response_description="Cliente encontrado.",
    responses={404: {"description": "Client not found"}},
)
def get_client_endpoint(
    client_id: UUID,
    db: Session = Depends(get_control_db),
) -> ClientRead:
    client = get_client_by_id(db, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return ClientRead.model_validate(client)


@router.delete(
    "/{client_id}",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover cliente",
    description="Remove (soft delete) um cliente/tenant, marcando-o como excluído sem apagar seu banco de dados.",
    responses={404: {"description": "Client not found"}},
)
def delete_client_endpoint(
    client_id: UUID,
    db: Session = Depends(get_control_db),
) -> None:
    deleted = soft_delete_client(db, client_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
