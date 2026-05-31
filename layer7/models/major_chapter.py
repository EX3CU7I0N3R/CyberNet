from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class MajorChapter(BaseModel):
    chapter_id: str
    chapter_type: str
    title: str
    description: str
    start_time: str
    end_time: str
    duration_seconds: float = 0.0
    event_count: int = 0
    phase_count: int = 0
    hosts: List[str] = Field(default_factory=list)
    key_events: List[str] = Field(default_factory=list)
    severity: str = "INFO"
    importance: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
