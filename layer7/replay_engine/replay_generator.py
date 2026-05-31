from __future__ import annotations

from layer7.models import TimelineIndex

from .frame_builder import FrameBuilder
from .state_reconstructor import StateReconstructor


class ReplayGenerator:
    MAX_FRAMES = 500

    def __init__(self):
        self.frame_builder = FrameBuilder()
        self.reconstructor = StateReconstructor()

    def generate(self, events, graph_state, investigation_candidates):
        frame_events = self._select_frame_events(events)
        frames = []
        previous_state = None

        for index, event in enumerate(frame_events):
            if index == len(frame_events) - 1:
                state = self.reconstructor.final_state(event.timestamp, graph_state, events, investigation_candidates)
            else:
                state = self.reconstructor.reconstruct(event.timestamp, graph_state, events, investigation_candidates)
            next_timestamp = frame_events[index + 1].timestamp if index + 1 < len(frame_events) else None
            frame = self.frame_builder.build(index + 1, event, state, previous_state, next_timestamp)
            frames.append(frame)
            previous_state = state

        return frames, self._index(events, frames)

    def _select_frame_events(self, events):
        if len(events) <= self.MAX_FRAMES:
            return list(events)

        important_types = {
            "beaconing_started",
            "hypothesis_created",
            "hypothesis_promoted",
            "candidate_created",
            "candidate_priority_changed",
            "narrative_generated",
            "host_risk_increased",
        }
        important = [event for event in events if event.event_type in important_types or event.severity in {"HIGH", "CRITICAL"}]
        remaining_capacity = max(self.MAX_FRAMES - len(important), 0)
        stride = max(1, len(events) // max(remaining_capacity, 1))
        sampled = [event for index, event in enumerate(events) if index % stride == 0]
        selected = {event.event_id: event for event in sampled[:remaining_capacity] + important}
        return sorted(selected.values(), key=lambda event: (event.timestamp, event.event_id))

    def _index(self, events, frames):
        host_event_offsets = {}
        for index, event in enumerate(events):
            host_event_offsets.setdefault(event.host, []).append(index)

        return TimelineIndex(
            frame_count=len(frames),
            event_count=len(events),
            start_time=events[0].timestamp if events else "",
            end_time=events[-1].timestamp if events else "",
            frame_ids=[frame.frame_id for frame in frames],
            event_ids=[event.event_id for event in events],
            event_offsets={event.event_id: index for index, event in enumerate(events)},
            frame_offsets={frame.frame_id: index for index, frame in enumerate(frames)},
            host_event_offsets=host_event_offsets,
        )
