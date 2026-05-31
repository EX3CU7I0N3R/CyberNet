from __future__ import annotations

from datetime import datetime, timezone

from layer7.models import ReplayFrame


class FrameBuilder:
    def build(self, frame_index: int, event, state, previous_state=None, next_timestamp: str | None = None):
        timestamp_delta = self._timestamp_delta(event.timestamp, next_timestamp)
        return ReplayFrame(
            frame_id=f"frame_{frame_index:05d}",
            timestamp=event.timestamp,
            state=state,
            delta=self._delta(previous_state, state, event),
            frame_duration=timestamp_delta,
            timestamp_delta=timestamp_delta,
            metadata={
                "trigger_event_id": event.event_id,
                "trigger_event_type": event.event_type,
                "supported_speeds": [1, 2, 4, 8, 16, 32],
            },
        )

    def _delta(self, previous_state, state, event):
        if previous_state is None:
            return {
                "added_nodes": state.nodes,
                "removed_nodes": [],
                "added_edges": state.edges,
                "removed_edges": [],
                "new_events": [event.model_dump()],
            }

        previous_nodes = {node["id"]: node for node in previous_state.nodes}
        current_nodes = {node["id"]: node for node in state.nodes}
        previous_edges = {edge["id"]: edge for edge in previous_state.edges}
        current_edges = {edge["id"]: edge for edge in state.edges}

        return {
            "added_nodes": [current_nodes[node_id] for node_id in current_nodes.keys() - previous_nodes.keys()],
            "removed_nodes": [previous_nodes[node_id] for node_id in previous_nodes.keys() - current_nodes.keys()],
            "added_edges": [current_edges[edge_id] for edge_id in current_edges.keys() - previous_edges.keys()],
            "removed_edges": [previous_edges[edge_id] for edge_id in previous_edges.keys() - current_edges.keys()],
            "new_events": [event.model_dump()],
        }

    def _timestamp_delta(self, timestamp: str, next_timestamp: str | None) -> float:
        if not next_timestamp:
            return 0.0
        return max(0.0, (self._parse(next_timestamp) - self._parse(timestamp)).total_seconds())

    def _parse(self, timestamp: str) -> datetime:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
