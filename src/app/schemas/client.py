from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class ClientCreate(BaseModel):
    slug: str = Field(
        min_length=1,
        max_length=100,
        pattern=SLUG_PATTERN,
        description=(
            "Identificador único e legível do cliente/tenant, usado como chave natural em toda a API "
            "(ex.: em referências e buscas). Apenas minúsculas, números e hífens."
        ),
        examples=["acme-corp"],
    )
    name: str = Field(
        min_length=1,
        max_length=255,
        description="Nome de exibição do cliente/tenant.",
        examples=["Acme Corporation"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"slug": "acme-corp", "name": "Acme Corporation"}]
        }
    )

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return value.strip().lower()


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class ClientListResponse(BaseModel):
    clients: list[ClientRead]
