"""Schemas do módulo de chat/consulta RAG de uma knowledge base."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """Trecho recuperado, com metadados de origem e relevância."""

    id: str = Field(description="Chunk ID")
    content: str | None = Field(default=None, description="Chunk content (LGPD)")
    title: str | None = Field(default=None, description="Document title (Cliente)")
    summary: str | None = Field(default=None, description="Document summary (Cliente)")
    article: str | None = Field(default=None, description="Article reference (LGPD)")
    section: str | None = Field(default=None, description="Section reference (LGPD)")
    score: float = Field(description="Relevance score")
    source: str = Field(description="Source: LGPD or Cliente")


class RagChatRequest(BaseModel):
    """Pergunta enviada ao chat de consulta RAG de uma knowledge base."""

    query: str = Field(
        min_length=1,
        description="Texto da pergunta a ser buscada via retrieval híbrido, nas versões da base.",
        examples=["Quais dados pessoais a tabela de usuários armazena e por quanto tempo?"],
    )


class RagChatResponse(BaseModel):
    """Resposta do chat: sempre traz o resultado do rascunho (EDIT, nunca exige publicação) e,
    quando existir uma versão publicada, também traz o resultado da PUBLISHED para comparação."""

    similarity_threshold: float = Field(
        description="Score mínimo de similaridade de cosseno usado para filtrar os trechos retornados."
    )
    latency_ms: int = Field(description="Tempo total de processamento da consulta, em milissegundos.")
    edited: list[RetrievedChunk] = Field(description="Trechos recuperados do conteúdo em edição (EDIT)")
    edited_answer: str | None = Field(default=None, description="Resposta gerada a partir do conteúdo em edição")
    published: list[RetrievedChunk] = Field(
        default_factory=list, description="Trechos recuperados do conteúdo publicado (PUBLISHED), se houver"
    )
    published_answer: str | None = Field(
        default=None, description="Resposta gerada a partir do conteúdo publicado, se houver"
    )
