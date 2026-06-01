from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ReplaySessionDTO(BaseModel):
    session_id: str
    frame_count: int
    duration: float


class ReplayFrameDTO(BaseModel):
    frame_id: int
    frame_key: str
    timestamp: str
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    candidate_hosts: List[Dict[str, Any]] = Field(default_factory=list)
    graph_metrics: Dict[str, Any] = Field(default_factory=dict)
    delta: Dict[str, Any] = Field(default_factory=dict)
    frame_duration: float = 0.0
    timestamp_delta: float = 0.0


class TimelineEventDTO(BaseModel):
    id: str
    timestamp: str
    type: str
    severity: str
    host: str
    related_hosts: List[str] = Field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActivityPhaseDTO(BaseModel):
    id: str
    name: str
    start_time: str
    end_time: str
    events: List[str] = Field(default_factory=list)
    description: str = ""


class ChapterDTO(BaseModel):
    id: int
    chapter_id: str
    title: str
    type: str
    description: str = ""
    start_time: str
    end_time: str
    duration_seconds: float = 0.0
    event_count: int = 0
    phase_count: int = 0
    hosts: List[str] = Field(default_factory=list)
    key_events: List[str] = Field(default_factory=list)
    severity: str = "INFO"
    importance: float = 0.0


class HostDTO(BaseModel):
    ip: str
    risk: float = 0.0
    role: str = "UNKNOWN"
    mac_address: str | None = None
    hostname: str | None = None
    user_identity: str | None = None
    user_full_name: str | None = None
    storyline: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[TimelineEventDTO] = Field(default_factory=list)
    chapters: List[Dict[str, Any]] = Field(default_factory=list)


class NarrativeDTO(BaseModel):
    host: str
    priority: str = "LOW"
    confidence: float = 0.0
    executive_summary: str = ""
    behavioral_summary: str = ""
    assessment: str = ""
    recommended_actions: List[str] = Field(default_factory=list)
    investigation_plan: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlaybackCommandDTO(BaseModel):
    action: str
    frame: int | None = None
    value: int | None = None


class ContextSummaryDTO(BaseModel):
    frame_count: int = 0
    duration: float = 0.0
    event_count: int = 0
    chapter_count: int = 0
    node_count: int = 0
    community_count: int = 0
    hypothesis_count: int = 0
    candidate_count: int = 0
    top_host: str | None = None
    primary_destination: str | None = None
    snapshot_quality: float | None = None
    validations: Dict[str, Any] = Field(default_factory=dict)


class RankedHostDTO(BaseModel):
    ip: str
    role: str = "UNKNOWN"
    role_confidence: float = 0.0
    community: str = "Unknown"
    mac_address: str | None = None
    hostname: str | None = None
    user_identity: str | None = None
    user_full_name: str | None = None
    risk: float = 0.0
    candidate_status: str = "none"
    finding_count: int = 0
    confidence: float = 0.0
    priority: str = "LOW"
    external_relationships: int = 0
    internal_relationships: int = 0
    top_protocols: List[str] = Field(default_factory=list)


class HypothesisContextDTO(BaseModel):
    hypothesis_id: str
    hypothesis_type: str = ""
    title: str = ""
    summary: str = ""
    impacted_entities: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    confidence_explanation: str = ""
    confidence: float = 0.0
    severity: str = ""
    priority_score: float = 0.0
    priority_level: str = ""
    finding_tier: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidateContextDTO(BaseModel):
    host: str
    host_role: str = "UNKNOWN"
    priority: str = "LOW"
    priority_score: float = 0.0
    priority_explanation: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    risk: float = 0.0
    candidate_rationale: str = ""
    host_summary: Dict[str, Any] = Field(default_factory=dict)
    rationale: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    narrative_context: Dict[str, Any] = Field(default_factory=dict)


class RelationshipContextDTO(BaseModel):
    edge_id: str
    source: str
    target: str
    risk: float = 0.0
    confidence: float = 0.0
    severity: str = ""
    protocols: List[str] = Field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    destination_rarity_score: float | None = None
    destination_exclusivity_score: float | None = None
    destination_consumer_count: int | None = None
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    confidence_explanation: str = ""


class DestinationContextDTO(BaseModel):
    ip: str
    related_host: str = ""
    risk: float = 0.0
    consumer_count: int | None = None
    rarity_score: float | None = None
    exclusivity_score: float | None = None
    contradictory_evidence: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    hypothesis_count: int = 0


class CommunityContextDTO(BaseModel):
    graph_nodes: int = 0
    classified_nodes: int = 0
    unclassified_nodes: int = 0
    community_distribution: Dict[str, int] = Field(default_factory=dict)
    role_count: Dict[str, int] = Field(default_factory=dict)
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    valid: bool = False


class ArtifactHealthDTO(BaseModel):
    graph_consistency: Dict[str, Any] = Field(default_factory=dict)
    hypothesis_validation: Dict[str, Any] = Field(default_factory=dict)
    candidate_validation: Dict[str, Any] = Field(default_factory=dict)
    snapshot_quality: Dict[str, Any] = Field(default_factory=dict)
    role_consistency: Dict[str, Any] = Field(default_factory=dict)
    layer6_readiness: Dict[str, Any] = Field(default_factory=dict)
