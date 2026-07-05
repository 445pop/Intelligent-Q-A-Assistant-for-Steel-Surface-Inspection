from __future__ import annotations

from pydantic import BaseModel, Field


class SimilarCaseHit(BaseModel):
    case_id: str
    score: float
    periodicity_label: str | None = None
    human_conclusion: str | None = None
    summary: str | None = None


class KnowledgeHit(BaseModel):
    doc_id: str
    title: str
    snippet: str
    source_priority: str = "medium"


class PeriodicDefectAnalysis(BaseModel):
    """疑似周期性缺陷 + 可解释结果（非最终裁决）。"""

    headline: str = Field(..., description="如：疑似周期性划伤")
    risk_level: str = Field(..., description="低/中/中高/高")
    periodicity_conclusion: str
    main_period_mm: float | None = None
    spacing_cv: float | None = None
    evidence_summary: str
    similar_case_count: int = 0
    similar_cases: list[SimilarCaseHit] = Field(default_factory=list)
    likely_causes: list[str] = Field(default_factory=list)
    suggested_checks: list[str] = Field(default_factory=list)
    knowledge_hits: list[KnowledgeHit] = Field(default_factory=list)
    disclaimer: str = Field(
        default="结论为智能辅助判断，需现场核查确认，不可替代人工裁决。"
    )
