from __future__ import annotations

from dataclasses import dataclass

from layer7.chapter_engine import ChapterManager
from layer7.event_engine import EventManager
from layer7.models import HostTimeline
from layer7.phase_engine import PhaseManager
from layer7.replay_engine import ReplayManager


@dataclass
class Layer7Result:
    timeline_events: list
    activity_phases: list
    replay_frames: list
    replay_index: object
    host_timelines: list
    major_chapters: list
    replay_coverage: float
    event_compression_ratio: float


class TimelineManager:
    def __init__(self):
        self.event_manager = EventManager()
        self.phase_manager = PhaseManager()
        self.replay_manager = ReplayManager()
        self.chapter_manager = ChapterManager()

    def build_timeline(
        self,
        canonical_events,
        enriched_flows,
        host_profiles,
        relationships,
        graph_state,
        hypotheses,
        investigation_candidates,
        investigation_narratives,
    ) -> Layer7Result:
        timeline_events = self.event_manager.build_events(
            enriched_flows=enriched_flows,
            host_profiles=host_profiles,
            relationships=relationships,
            graph_state=graph_state,
            hypotheses=hypotheses,
            investigation_candidates=investigation_candidates,
            investigation_narratives=investigation_narratives,
        )
        activity_phases = self.phase_manager.build_phases(timeline_events)
        replay_frames, replay_index = self.replay_manager.build_replay(
            timeline_events,
            graph_state,
            investigation_candidates,
        )
        major_chapters = self.chapter_manager.build_chapters(
            timeline_events,
            activity_phases,
            investigation_candidates,
        )
        host_timelines = self._host_timelines(timeline_events, major_chapters)
        return Layer7Result(
            timeline_events=timeline_events,
            activity_phases=activity_phases,
            replay_frames=replay_frames,
            replay_index=replay_index,
            host_timelines=host_timelines,
            major_chapters=major_chapters,
            replay_coverage=self._coverage(replay_frames, graph_state),
            event_compression_ratio=self._compression_ratio(timeline_events, canonical_events),
        )

    def _host_timelines(self, events, chapters=None):
        chapters = chapters or []
        events_by_host = {}
        for event in events:
            if event.host:
                events_by_host.setdefault(event.host, []).append({
                    "timestamp": event.timestamp,
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "severity": event.severity,
                    "description": event.description,
                    "related_hosts": event.related_hosts,
                })
        return [
            HostTimeline(host=host, events=host_events, chapters=self._chapters_for_host(host, chapters))
            for host, host_events in sorted(events_by_host.items())
        ]

    def _chapters_for_host(self, host, chapters):
        return [
            {
                "chapter_id": chapter.chapter_id,
                "title": chapter.title,
                "chapter_type": chapter.chapter_type,
                "start_time": chapter.start_time,
                "end_time": chapter.end_time,
                "importance": chapter.importance,
            }
            for chapter in chapters
            if host in chapter.hosts
        ]

    def _coverage(self, replay_frames, graph_state) -> float:
        if not replay_frames:
            return 0.0
        final_state = replay_frames[-1].state
        expected_nodes = max(getattr(graph_state, "node_count", 0), 1)
        expected_edges = max(getattr(graph_state, "edge_count", 0), 1)
        node_coverage = len(final_state.nodes) / expected_nodes
        edge_coverage = len(final_state.edges) / expected_edges
        return round(min((node_coverage + edge_coverage) / 2, 1.0) * 100, 2)

    def _compression_ratio(self, timeline_events, canonical_events) -> float:
        packet_count = max(len(canonical_events), 1)
        return round(len(timeline_events) / packet_count, 4)
