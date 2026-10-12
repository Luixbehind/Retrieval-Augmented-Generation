"""RAG retrieval service."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from rank_bm25 import BM25Okapi
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.content_environment import ContentEnvironmentEnum
from app.models.legal_chunk import LegalChunk
from app.models.legal_document import LegalDocument, LegalDocumentProcessingStatusEnum

DEFAULT_SIMILARITY_THRESHOLD = 0.1
DEFAULT_HYBRID_WEIGHT_BM25 = 0.7
DEFAULT_HYBRID_WEIGHT_VECTOR = 0.3


class RetrievalService:
    """Hybrid (BM25 + vetorial) retrieval service used pelos fluxos de LGPD e RAG."""

    def __init__(self, session: Session):
        self.session = session

    def _tokenize(self, text: str | None) -> list[str]:
        if not text:
            return []
        tokens: list[str] = []
        for token in text.lower().split():
            clean = token.strip('.,;:!?"\'()[]{}-_')
            if clean:
                tokens.append(clean)
        return tokens

    def _bm25_scores(self, query: str, documents: list[str]) -> list[float]:
        """Ranking BM25 (Robertson; Zaragoza, 2009) sobre o corpus de trechos candidatos,
        normalizado para 0..1 (pelo maior score) para poder ser combinado com a similaridade
        vetorial na fusão híbrida."""
        query_tokens = self._tokenize(query)
        if not query_tokens or not documents:
            return [0.0] * len(documents)

        corpus_tokens = [self._tokenize(doc) for doc in documents]
        bm25 = BM25Okapi(corpus_tokens)
        raw_scores = bm25.get_scores(query_tokens)
        max_score = max(raw_scores, default=0.0)
        if max_score <= 0:
            return [0.0] * len(documents)
        return [float(score) / max_score for score in raw_scores]

    async def retrieve_lgpd(
        self,
        embedding: list[float],
        query: str = "",
        top_k: int = 10,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        environment: ContentEnvironmentEnum = ContentEnvironmentEnum.PUBLISHED,
        knowledge_base_id: UUID | None = None,
        hybrid_weight_bm25: float = DEFAULT_HYBRID_WEIGHT_BM25,
        hybrid_weight_vector: float = DEFAULT_HYBRID_WEIGHT_VECTOR,
    ) -> list[dict[str, Any]]:
        conditions = [
            LegalDocument.deleted_at.is_(None),
            LegalDocument.environment == environment,
            LegalDocument.processing_status == LegalDocumentProcessingStatusEnum.COMPLETED,
        ]
        if knowledge_base_id is not None:
            conditions.append(LegalDocument.knowledge_base_id == knowledge_base_id)

        # Sem LIMIT aqui: o BM25 precisa das estatísticas (IDF) do corpus completo de trechos
        # candidatos para ranquear corretamente, não apenas dos vizinhos mais próximos por vetor.
        stmt = (
            select(
                LegalChunk.id,
                LegalChunk.content,
                LegalChunk.article,
                LegalChunk.section,
                LegalChunk.embedding.cosine_distance(embedding).label("distance"),
            )
            .join(LegalDocument, LegalDocument.id == LegalChunk.document_id)
            .where(*conditions)
            .order_by(text("distance"))
        )

        results = self.session.execute(stmt).fetchall()
        bm25_scores = self._bm25_scores(query, [row.content or "" for row in results])

        scored: list[dict[str, Any]] = []
        for row, bm25_score in zip(results, bm25_scores):
            similarity = float(1 - row.distance) if row.distance is not None else 0.0
            if similarity < similarity_threshold:
                continue
            score = (hybrid_weight_vector * similarity) + (hybrid_weight_bm25 * bm25_score)
            scored.append(
                {
                    "id": str(row.id),
                    "content": row.content,
                    "article": row.article,
                    "section": row.section,
                    "score": score,
                    "source": "LGPD",
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:top_k]
