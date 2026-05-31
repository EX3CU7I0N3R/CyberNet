from __future__ import annotations

from .event_builder import EventBuilder
from .event_correlator import EventCorrelator


class EventManager:
    def __init__(self):
        self.builder = EventBuilder()
        self.correlator = EventCorrelator()

    def build_events(
        self,
        enriched_flows,
        host_profiles,
        relationships,
        graph_state,
        hypotheses,
        investigation_candidates,
        investigation_narratives,
    ):
        events = self.builder.build(
            enriched_flows=enriched_flows,
            host_profiles=host_profiles,
            relationships=relationships,
            graph_state=graph_state,
            hypotheses=hypotheses,
            investigation_candidates=investigation_candidates,
            investigation_narratives=investigation_narratives,
        )
        return self.correlator.correlate(events)
