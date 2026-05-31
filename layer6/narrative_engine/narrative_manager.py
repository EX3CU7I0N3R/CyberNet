from __future__ import annotations

from .narrative_builder import NarrativeBuilder


class NarrativeManager:
    def __init__(self, narrative_builder: NarrativeBuilder | None = None):
        self.narrative_builder = narrative_builder or NarrativeBuilder()

    def build_narratives(self, investigation_candidates, host_profiles_by_ip=None, graph_context=None):
        host_profiles_by_ip = host_profiles_by_ip or {}
        narratives = []
        for candidate in investigation_candidates:
            narratives.append(
                self.narrative_builder.build(
                    candidate,
                    host_profile=host_profiles_by_ip.get(candidate.host),
                    graph_context=graph_context,
                )
            )
        return narratives
