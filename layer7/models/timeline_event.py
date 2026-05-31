from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class TimelineEvent(BaseModel):
    timestamp: str
    event_id: str
    event_type: str
    severity: str
    host: str
    related_hosts: List[str] = Field(default_factory=list)
    description: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
