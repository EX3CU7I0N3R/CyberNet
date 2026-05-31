from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class BehavioralDelta(BaseModel):
    delta_id: str
    entity_type: Literal["host", "relationship"]
    delta_type: str
    entity_id: str
    host_id: Optional[str] = None
    relationship_id: Optional[str] = None
    source_snapshot_id: Optional[str] = None
    target_snapshot_id: Optional[str] = None
    detected_at: str
    confidence: float = 0.0
    severity: str = "informational"
    summary: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    baseline_comparison: Optional[Dict[str, Any]] = None
    related_entities: List[str] = Field(default_factory=list)


class AttackHypothesis(BaseModel):
    hypothesis_id: str
    hypothesis_type: str
    title: str
    summary: str
    impacted_entities: List[str] = Field(default_factory=list)
    supporting_delta_ids: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    confidence_explanation: str = ""
    confidence: float = 0.0
    severity: str = "informational"
    priority_score: float = 0.0
    priority_level: str = "INFORMATIONAL"
    finding_tier: Literal["PRIMARY", "SECONDARY", "SUPPORTING"] = "SUPPORTING"
    asset_criticality_score: float = 0.0
    created_at: str
    status: str = "new"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    criticality_score: Optional[float] = None


class HostInvestigationSummary(BaseModel):
    host: str
    host_risk: float = 0.0
    hypothesis_count: int = 0
    highest_confidence: float = 0.0
    priority_score: float = 0.0
    asset_criticality_score: float = 0.0
    host_summary: Dict[str, Any] = Field(default_factory=dict)
    findings: List[AttackHypothesis] = Field(default_factory=list)


class InvestigationCandidate(BaseModel):
    host: str
    host_role: str = "UNKNOWN"
    priority: str = "LOW"
    priority_score: float = 0.0
    priority_explanation: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    risk: float = 0.0
    asset_criticality_score: float = 0.0
    candidate_rationale: str = ""
    host_summary: Dict[str, Any] = Field(default_factory=dict)
    rationale: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    narrative_context: Dict[str, Any] = Field(default_factory=dict)
    hypotheses: List[AttackHypothesis] = Field(default_factory=list)
    findings: List[AttackHypothesis] = Field(default_factory=list)


class HypothesisDefinition(BaseModel):
    hypothesis_type: str
    title: str
    description: str
    signals: List[str] = Field(default_factory=list)
    severity: str = "informational"
    confidence_weights: Dict[str, float] = Field(default_factory=dict)
    delta_requirements: Dict[str, Any] = Field(default_factory=dict)


class HostBaselineSummary(BaseModel):
    host_id: str
    risk_score_mean: float = 0.0
    risk_score_std: float = 0.0
    observed_protocols: Dict[str, int] = Field(default_factory=dict)
    average_persistence: float = 0.0
    unique_port_mean: float = 0.0
    sample_count: int = 0


class RelationshipBaselineSummary(BaseModel):
    relationship_id: str
    persistence_mean: float = 0.0
    persistence_std: float = 0.0
    observed_protocols: Dict[str, int] = Field(default_factory=dict)
    average_flow_count: float = 0.0
    sample_count: int = 0
