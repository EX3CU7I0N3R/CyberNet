from __future__ import annotations

from .phase_detector import PhaseDetector


class PhaseManager:
    def __init__(self):
        self.detector = PhaseDetector()

    def build_phases(self, events):
        return self.detector.detect(events)
