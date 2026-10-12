from __future__ import annotations

import json
import importlib
import re
import zipfile
from io import BytesIO
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

from app.core.config import settings

MAX_EMBEDDING_DIMENSION = 1536


def extract_document_text(file_bytes: bytes, file_name: str, mime_type: str | None) -> str:
    extension = Path(file_name).suffix.lower()

    if extension == ".json" or mime_type == "application/json":
        payload = json.loads(file_bytes.decode("utf-8-sig"))
        return json.dumps(payload, ensure_ascii=False, indent=2)

    if extension in {".sql", ".md", ".txt", ".csv"}:
        return file_bytes.decode("utf-8-sig", errors="replace").strip()

    if extension == ".pdf" or mime_type == "application/pdf":
        pypdf_module = importlib.import_module("pypdf")
        pdf_reader_cls = getattr(pypdf_module, "PdfReader")
        reader = pdf_reader_cls(BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages).strip()

    if extension == ".docx" or mime_type in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"}:
        try:
            with zipfile.ZipFile(BytesIO(file_bytes)) as docx_zip:
                content = docx_zip.read("word/document.xml")
            text = content.decode("utf-8", errors="ignore")
            text = re.sub(r"<w:t[^>]*>", " ", text)
            text = re.sub(r"</w:t>", " ", text)
            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"\s+", " ", text)
            return text.strip()
        except Exception:
            return file_bytes.decode("utf-8-sig", errors="replace").strip()

    return file_bytes.decode("utf-8-sig", errors="replace").strip()


def request_embedding(text: str) -> list[float]:
    response = call_ollama_json(
        "/api/embeddings",
        {
            "model": settings.embedding_model,
            "prompt": text,
        },
    )
    embedding = response.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise RuntimeError("LLM returned an empty embedding")
    return [float(value) for value in embedding]


def normalize_embedding(embedding: list[float], target_dimension: int = MAX_EMBEDDING_DIMENSION) -> list[float]:
    if len(embedding) == target_dimension:
        return embedding
    if len(embedding) > target_dimension:
        return embedding[:target_dimension]
    return embedding + [0.0] * (target_dimension - len(embedding))


def call_ollama_json(path: str, payload: dict[str, object]) -> dict[str, object]:
    url = f"{settings.ollama_base_url.rstrip('/')}" + path
    data = json.dumps(payload).encode("utf-8")
    http_request = urllib_request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(http_request, timeout=600) as response:
            raw_body = response.read().decode("utf-8")
            return json.loads(raw_body)
    except urllib_error.URLError as exc:  # noqa: BLE001 - propagate the precise failure to the caller
        raise RuntimeError(f"Failed to call Ollama at {path}: {exc}") from exc
