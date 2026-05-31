from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class InvestigationNarrative(BaseModel):
    host: str
    priority: str
    confidence: float = 0.0
    risk_context: Dict = Field(default_factory=dict)
    executive_summary: str = ""
    behavioral_summary: str = ""
    evidence_summary: str = ""
    investigation_reasoning: str = ""
    confidence_drivers: Dict[str, List[str]] = Field(default_factory=lambda: {"high": [], "medium": [], "low": []})
    negative_findings: List[str] = Field(default_factory=list)
    assessment: str = ""
    confidence_explanation: str = ""
    recommended_actions: List[str] = Field(default_factory=list)
    investigation_plan: List[str] = Field(default_factory=list)
    narrative_quality_score: float = 0.0
    supporting_hypotheses: List[str] = Field(default_factory=list)
