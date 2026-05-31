from __future__ import annotations

from layer8_backend.providers import ReplayArtifactProvider
from layer8_backend.replay import FrameQueryEngine, ReplaySessionEngine


class ReplayService:
    def __init__(self, artifact_dir: str = "output"):
        self.provider = ReplayArtifactProvider(artifact_dir)
        self.sessions = ReplaySessionEngine(self.provider)
        self.frames = FrameQueryEngine(self.provider)

    def create_session(self):
        return self.sessions.create_session()

    def get_frame(self, frame_id: int | str):
        return self.frames.get_frame(frame_id)

    def seek(self, timestamp: str):
        return self.frames.seek_time(timestamp)

    def chapter_jump(self, chapter_id: int | str):
        return self.frames.chapter_frame(chapter_id)

    def chapters(self):
        self.provider.load()
        return self.provider.chapters

    def events(self):
        self.provider.load()
        return self.provider.events

    def narratives(self):
        self.provider.load()
        return self.provider.narratives

    def host(self, ip: str):
        return self.provider.host(ip)

    def phases(self):
        self.provider.load()
        return self.provider.phases
