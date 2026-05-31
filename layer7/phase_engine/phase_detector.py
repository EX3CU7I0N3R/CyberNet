from __future__ import annotations

import hashlib
from typing import Iterable, List

from layer7.models import ActivityPhase

from .phase_classifier import PhaseClassifier


class PhaseDetector:
    def __init__(self):
        self.classifier = PhaseClassifier()

    def detect(self, events: Iterable) -> List[ActivityPhase]:
        phases = []
        active_events = []
        active_phase = None

        for event in events:
            phase_name = self.classifier.classify(event)
            if active_phase is None:
                active_phase = phase_name
            if phase_name != active_phase and active_events:
                phases.append(self._phase(active_phase, active_events))
                active_events = []
                active_phase = phase_name
            active_events.append(event)

        if active_events:
            phases.append(self._phase(active_phase or "Unknown", active_events))

        return phases

    def _phase(self, phase_name: str, events: list) -> ActivityPhase:
        phase_key = f"{phase_name}|{events[0].timestamp}|{events[-1].timestamp}|{len(events)}"
        phase_id = f"phase_{hashlib.md5(phase_key.encode('utf-8')).hexdigest()[:10]}"
        event_types = sorted({event.event_type for event in events})
        return ActivityPhase(
            phase_id=phase_id,
            phase_name=phase_name,
            start_time=events[0].timestamp,
            end_time=events[-1].timestamp,
            events=[event.event_id for event in events],
            description=f"{phase_name} phase containing {len(events)} correlated events: {', '.join(event_types[:5])}",
        )
