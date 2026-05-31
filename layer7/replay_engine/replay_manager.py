from __future__ import annotations

from .replay_generator import ReplayGenerator


class ReplayManager:
    def __init__(self):
        self.generator = ReplayGenerator()

    def build_replay(self, events, graph_state, investigation_candidates):
        return self.generator.generate(events, graph_state, investigation_candidates)
