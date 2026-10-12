from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.knowledge_base import GoldenDatasetStatusEnum, KnowledgeBaseStatusEnum


class KnowledgeBaseBase(BaseModel):
    name: str = Field(min_length=1, max_length=255, examples=["Base de Conhecimento - Cliente Acme"])
    description: str | None = Field(
        default=None,
        max_length=5000,
        examples=["Documentos internos e schema de banco da Acme para análise de conformidade LGPD."],
    )


class KnowledgeBaseCreate(KnowledgeBaseBase):
    type: str | None = Field(
        default=None,
        description="Categoria livre da base (ex.: 'lgpd_compliance', 'cliente', 'juridico').",
        examples=["cliente"],
    )
    config: dict | None = Field(
        default=None,
        description=(
            "Configuração de retrieval e avaliação da knowledge base. Se omitido, o banco aplica o default "
            "{'top_k': 5, 'hybrid_weight_bm25': 0.7, 'hybrid_weight_vector': 0.3, 'similarity_threshold': 0.1, "
            "'golden_dataset_size': 8}. 'golden_dataset_size' é a quantidade padrão de perguntas geradas por "
            "POST .../golden-questions/generate quando num_questions não é informado na chamada."
        ),
        examples=[
            {
                "top_k": 5,
                "hybrid_weight_bm25": 0.7,
                "hybrid_weight_vector": 0.3,
                "similarity_threshold": 0.1,
                "golden_dataset_size": 8,
            }
        ],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Base de Conhecimento - Cliente Acme",
                    "description": "Documentos internos e schema de banco da Acme para análise de conformidade LGPD.",
                    "type": "cliente",
                    "config": {
                        "top_k": 5,
                        "hybrid_weight_bm25": 0.7,
                        "hybrid_weight_vector": 0.3,
                        "similarity_threshold": 0.1,
                        "golden_dataset_size": 8,
                    },
                }
            ]
        }
    )


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=255, examples=["Base de Conhecimento - Cliente Acme (v2)"]
    )
    description: str | None = Field(
        default=None, max_length=5000, examples=["Atualizada após revisão contratual de 2026."]
    )
    config: dict | None = Field(
        default=None,
        description="Configuração de retrieval/avaliação a ser sobrescrita (campos omitidos mantêm o valor atual).",
        examples=[
            {
                "top_k": 8,
                "hybrid_weight_bm25": 0.6,
                "hybrid_weight_vector": 0.4,
                "similarity_threshold": 0.15,
                "golden_dataset_size": 12,
            }
        ],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "description": "Atualizada após revisão contratual de 2026.",
                    "config": {
                        "top_k": 8,
                        "hybrid_weight_bm25": 0.6,
                        "hybrid_weight_vector": 0.4,
                        "similarity_threshold": 0.15,
                        "golden_dataset_size": 12,
                    },
                }
            ]
        }
    )


class KnowledgeBaseRead(KnowledgeBaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str | None = None
    config: dict = Field(
        default_factory=lambda: {
            "top_k": 5,
            "hybrid_weight_bm25": 0.7,
            "hybrid_weight_vector": 0.3,
            "similarity_threshold": 0.1,
            "golden_dataset_size": 8,
        }
    )
    status: KnowledgeBaseStatusEnum = KnowledgeBaseStatusEnum.DRAFT
    golden_dataset_status: GoldenDatasetStatusEnum = Field(
        default=GoldenDatasetStatusEnum.IDLE,
        description=(
            "Status da (re)geração em background do golden dataset: IDLE (nunca rodou), PENDING "
            "(rodando agora — evite chamar /evaluations/runs até virar COMPLETED), COMPLETED ou FAILED."
        ),
    )
    golden_dataset_error_message: str | None = Field(
        default=None, description="Preenchido apenas quando golden_dataset_status é FAILED."
    )
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class KnowledgeBaseListResponse(BaseModel):
    bases: list[KnowledgeBaseRead]
