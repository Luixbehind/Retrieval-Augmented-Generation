"""Chat de consulta RAG de uma knowledge base.

Endpoint dedicado e independente de publicação: a base nunca precisa estar PUBLISHED para ser
testada aqui. A resposta do rascunho (EDIT) é sempre gerada; a versão publicada (PUBLISHED) só
entra na resposta quando já existir, para comparação lado a lado.
"""
from __future__ import annotations

import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tenant_db import get_tenant_db
from app.models.content_environment import ContentEnvironmentEnum
from app.models.knowledge_base import KnowledgeBase
from app.models.rag_query import RagQuery
from app.schemas.rag_chat import RagChatRequest, RagChatResponse, RetrievedChunk
from app.services.answer_generation import generate_report_answer
from app.services.document_processing import normalize_embedding, request_embedding
from app.services.retrieval_service import (
    DEFAULT_HYBRID_WEIGHT_BM25,
    DEFAULT_HYBRID_WEIGHT_VECTOR,
    DEFAULT_SIMILARITY_THRESHOLD,
    RetrievalService,
)

router = APIRouter(prefix="/knowledge-bases", tags=["rag-chat"])


def _to_retrieved_chunks(items: list[dict]) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            id=item["id"],
            content=item.get("content"),
            article=item.get("article"),
            section=item.get("section"),
            score=item["score"],
            source=item["source"],
        )
        for item in items
    ]


@router.post(
    "/{knowledge_base_id}/rag-chat",
    response_model=RagChatResponse,
    summary="Consultar RAG da knowledge base (chat)",
    description=(
        "Executa a pergunta contra o relatório de compliance em edição (EDIT) da knowledge base — "
        "não exige que a base esteja publicada. Se já houver uma versão publicada (PUBLISHED), a "
        "mesma pergunta também é respondida contra ela, para comparação lado a lado."
    ),
    response_description="Resposta do rascunho e, se existir, da versão publicada.",
    responses={404: {"description": "Knowledge base not found"}},
)
async def rag_chat_query(
    knowledge_base_id: UUID,
    payload: RagChatRequest,
    db: Session = Depends(get_tenant_db),
) -> RagChatResponse:
    kb = db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.deleted_at.is_(None),
        )
    ).scalar()
    if kb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    kb_config = kb.config or {}
    similarity_threshold = float(kb_config.get("similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD))
    hybrid_weight_bm25 = float(kb_config.get("hybrid_weight_bm25", DEFAULT_HYBRID_WEIGHT_BM25))
    hybrid_weight_vector = float(kb_config.get("hybrid_weight_vector", DEFAULT_HYBRID_WEIGHT_VECTOR))

    started_at = time.perf_counter()

    # As chamadas ao Ollama abaixo são síncronas/bloqueantes; rodá-las em threadpool evita
    # travar o event loop para as demais requisições da API enquanto elas estão em andamento.
    embedding = await run_in_threadpool(request_embedding, payload.query)
    normalized_embedding = normalize_embedding(embedding)
    retrieval_service = RetrievalService(db)

    edited_results = await retrieval_service.retrieve_lgpd(
        normalized_embedding,
        payload.query,
        similarity_threshold=similarity_threshold,
        environment=ContentEnvironmentEnum.EDIT,
        knowledge_base_id=knowledge_base_id,
        hybrid_weight_bm25=hybrid_weight_bm25,
        hybrid_weight_vector=hybrid_weight_vector,
    )
    published_results = await retrieval_service.retrieve_lgpd(
        normalized_embedding,
        payload.query,
        similarity_threshold=similarity_threshold,
        environment=ContentEnvironmentEnum.PUBLISHED,
        knowledge_base_id=knowledge_base_id,
        hybrid_weight_bm25=hybrid_weight_bm25,
        hybrid_weight_vector=hybrid_weight_vector,
    )

    edited_answer = await run_in_threadpool(generate_report_answer, payload.query, edited_results)
    published_answer = await run_in_threadpool(generate_report_answer, payload.query, published_results)

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    best_edited_score = max((item["score"] for item in edited_results), default=None)
    best_published_score = max((item["score"] for item in published_results), default=None)

    db.add(
        RagQuery(
            knowledge_base_id=knowledge_base_id,
            question=payload.query,
            edited_response=edited_answer,
            edited_score=best_edited_score,
            published_response=published_answer,
            published_score=best_published_score,
            latency_ms=latency_ms,
            model_name=settings.llm_model,
        )
    )
    db.commit()

    return RagChatResponse(
        similarity_threshold=similarity_threshold,
        latency_ms=latency_ms,
        edited=_to_retrieved_chunks(edited_results),
        edited_answer=edited_answer,
        published=_to_retrieved_chunks(published_results),
        published_answer=published_answer,
    )
