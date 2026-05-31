from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ActivityPhase(BaseModel):
    phase_id: str
    phase_name: str
    start_time: str
    end_time: str
    events: List[str] = Field(default_factory=list)
    description: str = ""
