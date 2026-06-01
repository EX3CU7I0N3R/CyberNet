from __future__ import annotations

import shutil
from pathlib import Path

from layer8_backend.providers import ReplayArtifactProvider
from layer8_backend.replay import FrameQueryEngine, ReplaySessionEngine


class ReplayService:
    def __init__(self, artifact_dir: str = "output"):
        self.artifact_dir = artifact_dir
        self.provider = ReplayArtifactProvider(artifact_dir)
        self.sessions = ReplaySessionEngine(self.provider)
        self.frames = FrameQueryEngine(self.provider)

    def reload(self):
        self.provider = ReplayArtifactProvider(self.artifact_dir)
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

    def summary(self):
        return self.provider.summary()

    def ranked_hosts(self):
        self.provider.load()
        return self.provider.ranked_hosts

    def hypotheses(self):
        self.provider.load()
        return self.provider.hypotheses

    def candidates(self):
        self.provider.load()
        return self.provider.candidates

    def relationships(self, host: str | None = None):
        return self.provider.relationships_for(host)

    def destinations(self):
        self.provider.load()
        return self.provider.destinations

    def community(self):
        self.provider.load()
        return self.provider.community

    def artifact_health(self):
        self.provider.load()
        return self.provider.health

    def runtime_logs(self, lines: int = 120):
        artifact_path = Path(self.artifact_dir)
        return {
            "stdout": self._tail_log(artifact_path / "layer8_backend.stdout.log", lines),
            "stderr": self._tail_log(artifact_path / "layer8_backend.stderr.log", lines),
            "health": self.artifact_health().model_dump(),
        }

    def clear_artifacts(self):
        artifact_path = Path(self.artifact_dir).resolve()
        artifact_path.mkdir(parents=True, exist_ok=True)
        cleared = []
        preserved = []

        for child in artifact_path.iterdir():
            if child.name == "uploads" or child.name.startswith("layer8_backend."):
                preserved.append(child.name)
                continue

            cleared.append(child.name)
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

        self.reload()
        return {"cleared": sorted(cleared), "preserved": sorted(preserved)}

    @staticmethod
    def _tail_log(path: Path, lines: int):
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
