from __future__ import annotations

from .chapter_builder import ChapterBuilder
from .chapter_correlator import ChapterCorrelator


class ChapterManager:
    def __init__(self):
        self.builder = ChapterBuilder()
        self.correlator = ChapterCorrelator()

    def build_chapters(self, timeline_events, activity_phases, investigation_candidates):
        chapters = self.builder.build(timeline_events, activity_phases, investigation_candidates)
        return self.correlator.correlate(chapters)
