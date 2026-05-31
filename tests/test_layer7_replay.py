import unittest

from behavior.schemas import GraphEdge, GraphNode, GraphState
from layer5.schemas import AttackHypothesis, InvestigationCandidate
from layer7.models import TimelineEvent
from layer7.replay_engine import ReplayManager


class TestLayer7Replay(unittest.TestCase):
    def test_replay_frames_are_sorted_and_render_ready(self):
        frames, index = ReplayManager().build_replay(
            self._events(),
            self._graph_state(),
            [self._candidate()],
        )

        self.assertGreater(len(frames), 0)
        self.assertEqual([frame.timestamp for frame in frames], sorted(frame.timestamp for frame in frames))
        self.assertEqual(index.frame_count, len(frames))
        self.assertIn("nodes", frames[-1].state.model_dump())
        self.assertEqual(len(frames[-1].state.nodes), 2)
        self.assertEqual(len(frames[-1].state.edges), 1)
        self.assertIn("new_events", frames[-1].delta)

    def _events(self):
        return [
            TimelineEvent(event_id="e1", timestamp="2026-05-31T00:00:00Z", event_type="host_role_assigned", severity="INFO", host="10.2.28.88", description="role"),
            TimelineEvent(event_id="e2", timestamp="2026-05-31T00:00:01Z", event_type="relationship_created", severity="LOW", host="10.2.28.88", related_hosts=["45.131.214.85"], description="relationship"),
            TimelineEvent(event_id="e3", timestamp="2026-05-31T00:00:02Z", event_type="candidate_created", severity="HIGH", host="10.2.28.88", description="candidate"),
        ]

    def _graph_state(self):
        return GraphState(
            snapshot_id="graph",
            timestamp="2026-05-31T00:00:00Z",
            node_count=2,
            edge_count=1,
            nodes=[
                GraphNode(node_id="10.2.28.88", ip_address="10.2.28.88", first_seen="2026-05-31T00:00:00Z"),
                GraphNode(node_id="45.131.214.85", ip_address="45.131.214.85", first_seen="2026-05-31T00:00:01Z"),
            ],
            edges=[
                GraphEdge(edge_id="e1", source_node="10.2.28.88", target_node="45.131.214.85", first_seen="2026-05-31T00:00:01Z")
            ],
        )

    def _candidate(self):
        hypothesis = AttackHypothesis(
            hypothesis_id="h1",
            hypothesis_type="beaconing",
            title="Beaconing",
            summary="Beaconing",
            impacted_entities=["10.2.28.88", "45.131.214.85"],
            created_at="2026-05-31T00:00:02Z",
        )
        return InvestigationCandidate(host="10.2.28.88", findings=[hypothesis], hypotheses=[hypothesis])


if __name__ == "__main__":
    unittest.main()
