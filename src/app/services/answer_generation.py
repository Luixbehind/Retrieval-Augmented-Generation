from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.prompts.lgpd_analysis import build_report_answer_prompt
from app.services.document_processing import call_ollama_json


def generate_report_answer(query: str, chunks: list[dict[str, Any]]) -> str | None:
    """Gera uma resposta em linguagem natural para a pergunta, usando os trechos do relatório recuperados como contexto."""
    report_context = "\n\n".join(
        f"[{chunk.get('article') or 'Trecho'}] {chunk.get('content') or ''}".strip()
        for chunk in chunks
        if chunk.get("content")
    ).strip()

    if not report_context:
        return None

    prompt = build_report_answer_prompt(report_context=report_context, question=query)
    response = call_ollama_json(
        "/api/generate",
        {
            "model": settings.llm_model,
            "prompt": prompt,
            "stream": False,
        },
    )
    answer = str(response.get("response", "")).strip()
    return answer or None
