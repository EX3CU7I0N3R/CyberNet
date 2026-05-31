from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from layer8_backend.providers import ReplayArtifactProvider
from layer8_backend.schemas import ReplaySessionDTO


@dataclass
class ReplaySession:
    session_id: str
    created_at: str
    current_frame: int = 1
    playing: bool = False
    speed: int = 1


class ReplaySessionEngine:
    def __init__(self, provider: ReplayArtifactProvider):
        self.provider = provider
        self.sessions: dict[str, ReplaySession] = {}

    def create_session(self) -> ReplaySessionDTO:
        self.provider.load()
        session_id = uuid.uuid4().hex
        self.sessions[session_id] = ReplaySession(
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )
        return ReplaySessionDTO(
            session_id=session_id,
            frame_count=len(self.provider.frames),
            duration=self.provider.duration_seconds(),
        )

    def playback_state(self, session_id: str) -> ReplaySession:
        session = self.sessions.get(session_id)
        if session is None:
            raise KeyError(f"Replay session not found: {session_id}")
        return session
