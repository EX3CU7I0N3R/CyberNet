from __future__ import annotations

from datetime import datetime, timezone

from layer7.models import ReplayState


class StateReconstructor:
    def reconstruct(self, timestamp: str, graph_state, events, investigation_candidates):
        active_events = [event for event in events if self._lte(event.timestamp, timestamp)]
        nodes = [self._node_payload(node) for node in getattr(graph_state, "nodes", []) if self._visible(node.first_seen, timestamp)]
        edges = [self._edge_payload(edge) for edge in getattr(graph_state, "edges", []) if self._visible(edge.first_seen, timestamp)]
        candidate_hosts = [self._candidate_payload(candidate) for candidate in investigation_candidates if self._candidate_visible(candidate, timestamp)]

        return ReplayState(
            timestamp=timestamp,
            nodes=nodes,
            edges=edges,
            events=[event.model_dump() for event in active_events[-25:]],
            active_relationships=edges,
            candidate_hosts=candidate_hosts,
            graph_metrics={
                "node_count": len(nodes),
                "edge_count": len(edges),
                "graph_density": getattr(graph_state, "graph_density", 0.0),
                "graph_risk_score": getattr(graph_state, "graph_risk_score", 0.0),
                "isolated_node_count": getattr(graph_state, "isolated_node_count", 0),
            },
        )

    def final_state(self, timestamp: str, graph_state, events, investigation_candidates):
        return ReplayState(
            timestamp=timestamp,
            nodes=[self._node_payload(node) for node in getattr(graph_state, "nodes", [])],
            edges=[self._edge_payload(edge) for edge in getattr(graph_state, "edges", [])],
            events=[event.model_dump() for event in events[-25:]],
            active_relationships=[self._edge_payload(edge) for edge in getattr(graph_state, "edges", [])],
            candidate_hosts=[self._candidate_payload(candidate) for candidate in investigation_candidates],
            graph_metrics={
                "node_count": getattr(graph_state, "node_count", 0),
                "edge_count": getattr(graph_state, "edge_count", 0),
                "graph_density": getattr(graph_state, "graph_density", 0.0),
                "graph_risk_score": getattr(graph_state, "graph_risk_score", 0.0),
                "isolated_node_count": getattr(graph_state, "isolated_node_count", 0),
            },
        )

    def _node_payload(self, node):
        return {
            "id": node.node_id,
            "ip": node.ip_address,
            "role": node.role,
            "risk_score": node.risk_score,
            "confidence": node.confidence,
            "community": node.metadata.get("community", "UNKNOWN"),
            "first_seen": node.first_seen,
            "last_seen": node.last_seen,
            "metadata": node.metadata,
        }

    def _edge_payload(self, edge):
        return {
            "id": edge.edge_id,
            "source": edge.source_node,
            "target": edge.target_node,
            "relationship_type": edge.relationship_type,
            "risk_score": edge.relationship_risk,
            "persistence_score": edge.persistence_score,
            "first_seen": edge.first_seen,
            "last_seen": edge.last_seen,
            "metadata": edge.metadata,
        }

    def _candidate_payload(self, candidate):
        return {
            "host": candidate.host,
            "priority": candidate.priority,
            "priority_score": candidate.priority_score,
            "confidence": candidate.confidence,
            "risk": candidate.risk,
            "role": candidate.host_role,
        }

    def _candidate_visible(self, candidate, timestamp: str) -> bool:
        findings = getattr(candidate, "findings", []) or getattr(candidate, "hypotheses", [])
        if not findings:
            return True
        return self._lte(getattr(findings[0], "created_at", ""), timestamp)

    def _visible(self, first_seen: str | None, timestamp: str) -> bool:
        if not first_seen:
            return True
        return self._lte(first_seen, timestamp)

    def _lte(self, left: str, right: str) -> bool:
        if not left or not right:
            return True
        return self._parse(left) <= self._parse(right)

    def _parse(self, timestamp: str) -> datetime:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
