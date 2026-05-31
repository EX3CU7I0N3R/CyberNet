from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ReplayState(BaseModel):
    timestamp: str
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    edges: List[Dict[str, Any]] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    active_relationships: List[Dict[str, Any]] = Field(default_factory=list)
    candidate_hosts: List[Dict[str, Any]] = Field(default_factory=list)
    graph_metrics: Dict[str, Any] = Field(default_factory=dict)


class TimelineIndex(BaseModel):
    frame_count: int = 0
    event_count: int = 0
    start_time: str = ""
    end_time: str = ""
    frame_ids: List[str] = Field(default_factory=list)
    event_ids: List[str] = Field(default_factory=list)
    event_offsets: Dict[str, int] = Field(default_factory=dict)
    frame_offsets: Dict[str, int] = Field(default_factory=dict)
    host_event_offsets: Dict[str, List[int]] = Field(default_factory=dict)
    supported_speeds: List[int] = Field(default_factory=lambda: [1, 2, 4, 8, 16, 32])


class HostTimeline(BaseModel):
    host: str
    events: List[Dict[str, Any]] = Field(default_factory=list)
    chapters: List[Dict[str, Any]] = Field(default_factory=list)
