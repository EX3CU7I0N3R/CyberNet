from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from .replay_state import ReplayState


class ReplayFrame(BaseModel):
    frame_id: str
    timestamp: str
    state: ReplayState
    delta: Dict[str, Any] = Field(default_factory=dict)
    frame_duration: float = 0.0
    timestamp_delta: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
