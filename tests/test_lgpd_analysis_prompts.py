from fastapi.testclient import TestClient

from app.main import app
from app.prompts.lgpd_analysis import (
    build_compliance_report_prompt,
    build_schema_analysis_prompt,
    build_structured_schema_terms_prompt,
)
from app.schemas.lgpd_compliance import LgpdComplianceResponse
from app.services import lgpd_compliance_service as compliance_service
from app.services.document_processing import extract_document_text
from app.services.lgpd_compliance_service import build_readable_report_html, build_report_sections


def test_schema_prompt_requires_structured_compliance_analysis():
    prompt = build_schema_analysis_prompt("lgpd", "CREATE TABLE clientes (...)")

    assert "Pontos corretos" in prompt
    assert "Pontos fora da lei" in prompt
    assert "Artigos da LGPD" in prompt


def test_compliance_report_prompt_requires_structured_output():
    prompt = build_compliance_report_prompt(
        lgpd_context="lei",
        document_content="schema + termo",
        previous_analysis="status inicial",
    )

    assert "## 1. Resumo executivo" in prompt
    assert "Pontos corretos" in prompt
    assert "Pontos fora da lei" in prompt
    assert "Recomendações" in prompt


def test_extract_document_text_supports_sql_schema_uploads():
    source = "CREATE TABLE usuarios (id SERIAL PRIMARY KEY, email TEXT, consentimento BOOLEAN);"
    extracted = extract_document_text(source.encode("utf-8"), "schema.sql", None)

    assert "CREATE TABLE usuarios" in extracted
    assert "consentimento" in extracted


def test_structured_prompt_requires_json_output():
    prompt = build_structured_schema_terms_prompt(
        lgpd_context="lei",
        schema_sql="CREATE TABLE usuarios (email TEXT);",
        terms_text="Termo de consentimento para uso de dados pessoais.",
    )

    assert "Responda APENAS em JSON válido" in prompt
    assert '"overall_status"' in prompt
    assert '"points_correct"' in prompt
    assert '"points_outside_law"' in prompt


def test_lgpd_compliance_response_validates_structured_payload():
    payload = {
        "overall_status": "PARTIAL",
        "summary": "Há alguns itens parcialmente adequados.",
        "points_correct": ["Há consentimento explícito."],
        "points_outside_law": ["Falta base legal clara para compartilhamento."],
        "applicable_articles": [{"article": "Art. 5º", "description": "Consentimento e finalidade."}],
        "risks": ["Uso indevido de dados pessoais."],
        "recommendations": ["Registrar consentimento e limitar finalidades."],
    }

    validated = LgpdComplianceResponse.model_validate(payload)
    assert validated.overall_status == "PARTIAL"
    assert validated.points_correct


def test_report_sections_are_ready_for_vector_index():
    report = LgpdComplianceResponse.model_validate({
        "overall_status": "PARTIAL",
        "summary": "Resumo do sistema.",
        "points_correct": ["Consentimento explícito."],
        "points_outside_law": ["Falta finalidade específica."],
        "applicable_articles": [{"article": "Art. 5º", "description": "Finalidade e consentimento."}],
        "risks": ["Risco de vazamento."],
        "recommendations": ["Registrar consentimento."],
    })

    sections = build_report_sections(report)

    assert any("resumo executivo" in title.lower() for title, _ in sections)
    assert any("pontos corretos" in title.lower() for title, _ in sections)
    assert any("pontos fora da lei" in title.lower() for title, _ in sections)
    assert any("recomendações" in title.lower() for title, _ in sections)


def test_readable_report_export_renders_user_friendly_sections():
    report = LgpdComplianceResponse.model_validate({
        "overall_status": "PARCIAL",
        "summary": "O sistema precisa ajustar consentimento e retenção de dados.",
        "points_correct": ["Há registro de finalidade específica."],
        "points_outside_law": ["Falta consentimento explícito para compartilhamento."],
        "applicable_articles": [{"article": "Art. 5º", "description": "Consentimento e finalidade."}],
        "risks": ["Risco de vazamento de dados pessoais."],
        "recommendations": ["Implementar consentimento claro e limite de retenção."],
    })

    html = build_readable_report_html("Relatório de conformidade LGPD", build_report_sections(report))

    assert "Relatório de conformidade LGPD" in html
    assert "Resumo executivo" in html
    assert "Pontos corretos" in html
    assert "Recomendações" in html
    assert "Implementar consentimento claro" in html


def test_report_files_are_persisted_for_download_and_listing(tmp_path, monkeypatch):
    monkeypatch.setattr(compliance_service, "REPORT_STORAGE_DIR", tmp_path)
    metadata = compliance_service.persist_report_files(
        "123e4567-e89b-12d3-a456-426614174000",
        "Relatório de conformidade LGPD",
        [("Resumo executivo", "Resumo do sistema."), ("Recomendações", "Implementar consentimento.")],
    )

    assert metadata["html_path"].exists()
    assert metadata["pdf_path"].exists()
    assert "Resumo do sistema." in metadata["html_path"].read_text(encoding="utf-8")
    assert "Implementar consentimento." in compliance_service.list_report_metadata()[0]["title"]


def test_report_download_requires_valid_api_key(monkeypatch):
    from app.api.v1 import endpoints as lgpd_endpoints_module
    from app.core.tenant_db import get_tenant_db
    from app.models.legal_document import LegalDocumentProcessingStatusEnum

    class _FakeCompletedDocument:
        deleted_at = None
        processing_status = LegalDocumentProcessingStatusEnum.COMPLETED

    class _FakeDb:
        def get(self, _model, _id):
            return _FakeCompletedDocument()

    monkeypatch.setattr("app.core.config.settings.report_download_api_key", "top-secret")
    monkeypatch.setattr(
        lgpd_endpoints_module.lgpd_compliance,
        "get_report_sections_by_id",
        lambda _db, _report_id: ("Relatório de conformidade", [("Resumo executivo", "Resumo do sistema.")]),
    )
    app.dependency_overrides[get_tenant_db] = lambda: _FakeDb()

    try:
        client = TestClient(app)

        response = client.get(
            "/api/v1/lgpd-compliance/report/123e4567-e89b-12d3-a456-426614174000/download?format=html",
            headers={"X-API-Key": "wrong-key", "X-Client-Slug": "acme-corp"},
        )

        assert response.status_code == 401

        authorized = client.get(
            "/api/v1/lgpd-compliance/report/123e4567-e89b-12d3-a456-426614174000/download?format=html",
            headers={"X-API-Key": "top-secret", "X-Client-Slug": "acme-corp"},
        )

        assert authorized.status_code == 200
        assert "Relatório de conformidade" in authorized.text
    finally:
        app.dependency_overrides.pop(get_tenant_db, None)
