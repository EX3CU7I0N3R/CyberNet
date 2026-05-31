from __future__ import annotations

from layer8_backend.providers import ReplayArtifactProvider


class FrameQueryEngine:
    def __init__(self, provider: ReplayArtifactProvider):
        self.provider = provider

    def get_frame(self, frame_id: int | str):
        return self.provider.frame(frame_id)

    def seek_time(self, timestamp: str):
        return self.provider.seek(timestamp)

    def chapter_frame(self, chapter_id: int | str):
        self.provider.load()
        chapter = self._chapter(chapter_id)
        return self.provider.seek(chapter.start_time)

    def _chapter(self, chapter_id: int | str):
        key = str(chapter_id)
        for chapter in self.provider.chapters:
            if str(chapter.id) == key or chapter.chapter_id == key:
                return chapter
        raise KeyError(f"Chapter not found: {chapter_id}")
