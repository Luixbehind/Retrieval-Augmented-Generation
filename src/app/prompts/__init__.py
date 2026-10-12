from __future__ import annotations

from app.prompts.lgpd_analysis import (
    PromptTemplates,
    build_schema_analysis_prompt,
    build_terms_analysis_prompt,
    build_compliance_report_prompt,
)

__all__ = [
    "PromptTemplates",
    "build_schema_analysis_prompt",
    "build_terms_analysis_prompt",
    "build_compliance_report_prompt",
]
