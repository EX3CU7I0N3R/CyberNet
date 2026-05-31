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
    created_at: str
    status: str = "new"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    criticality_score: Optional[float] = None


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
