from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApplicableArticle(BaseModel):
    article: str
    description: str


class LgpdComplianceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_status: str
    summary: str
    points_correct: list[str]
    points_outside_law: list[str]
    applicable_articles: list[ApplicableArticle]
    risks: list[str]
    recommendations: list[str]
    report_id: str | None = Field(default=None, description="Identificador do relatório persistido para download.")


class LgpdComplianceStatusResponse(BaseModel):
    """Status de uma análise de conformidade LGPD, rodando em background."""

    model_config = ConfigDict(extra="forbid")

    report_id: str
    processing_status: Literal["PENDING", "COMPLETED", "FAILED"]
    error_message: str | None = Field(default=None, description="Preenchido apenas quando processing_status é FAILED.")
    result: LgpdComplianceResponse | None = Field(
        default=None, description="Preenchido apenas quando processing_status é COMPLETED."
    )
    schema_file_name: str | None = Field(
        default=None, description="Nome do arquivo de schema enviado nesta análise."
    )
    terms_file_name: str | None = Field(
        default=None, description="Nome do arquivo de termo de compromisso enviado nesta análise."
    )
