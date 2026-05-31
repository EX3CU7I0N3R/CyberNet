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
