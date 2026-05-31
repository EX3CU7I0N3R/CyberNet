import unittest
from types import SimpleNamespace

from behavior.schemas import GraphEdge, GraphNode, GraphState, HostProfile, HostRelationship
from layer5.schemas import AttackHypothesis, InvestigationCandidate
from layer7 import TimelineManager


class TestLayer7Events(unittest.TestCase):
    def test_timeline_events_are_correlated_and_sorted(self):
        result = TimelineManager().build_timeline(
            canonical_events=self._canonical_events(100),
            enriched_flows=self._flows(),
            host_profiles=self._host_profiles(),
            relationships=self._relationships(),
            graph_state=self._graph_state(),
            hypotheses=[self._hypothesis()],
            investigation_candidates=[self._candidate()],
            investigation_narratives=[],
        )

        self.assertGreater(len(result.timeline_events), 0)
        self.assertLess(result.event_compression_ratio, 0.25)
        self.assertEqual(
            [event.timestamp for event in result.timeline_events],
            sorted(event.timestamp for event in result.timeline_events),
        )
        self.assertIn("candidate_created", {event.event_type for event in result.timeline_events})

    def _canonical_events(self, count):
        return [SimpleNamespace(timestamp=f"2026-05-31T00:{index:02d}:00Z") for index in range(count)]

    def _flows(self):
        return [
            SimpleNamespace(
                flow_id="f1",
                timestamp_first="2026-05-31T00:00:01Z",
                initiator_ip="10.2.28.88",
                responder_ip="45.131.214.85",
                application_protocol="https",
                responder_port=443,
                packet_count=50,
                initiator_bytes=1000,
                responder_bytes=500,
                behavioral_score=75.0,
            ),
            SimpleNamespace(
                flow_id="f2",
                timestamp_first="2026-05-31T00:00:02Z",
                initiator_ip="10.2.28.88",
                responder_ip="10.2.28.2",
                application_protocol="dns",
                responder_port=53,
                packet_count=5,
                initiator_bytes=300,
                responder_bytes=600,
                behavioral_score=0.0,
            ),
        ]

    def _host_profiles(self):
        return [
            HostProfile(ip_address="10.2.28.88", role="WORKSTATION", first_seen="2026-05-31T00:00:00Z", risk_score=74.0),
            HostProfile(ip_address="45.131.214.85", role="EXTERNAL_SERVICE", first_seen="2026-05-31T00:00:01Z", risk_score=55.0),
        ]

    def _relationships(self):
        return [
            HostRelationship(
                edge_id="r1",
                source="10.2.28.88",
                target="45.131.214.85",
                relationship_risk=80.0,
                first_seen="2026-05-31T00:00:01Z",
                packet_count=50,
                total_bytes=1500,
                persistence=0.8,
                protocols=["https"],
            )
        ]

    def _graph_state(self):
        return GraphState(
            snapshot_id="graph",
            timestamp="2026-05-31T00:00:00Z",
            node_count=2,
            edge_count=1,
            nodes=[
                GraphNode(node_id="10.2.28.88", ip_address="10.2.28.88", role="WORKSTATION", risk_score=74.0, first_seen="2026-05-31T00:00:00Z", metadata={"community": "WORKSTATIONS"}),
                GraphNode(node_id="45.131.214.85", ip_address="45.131.214.85", role="EXTERNAL_SERVICE", risk_score=55.0, first_seen="2026-05-31T00:00:01Z", metadata={"community": "EXTERNAL_SERVICES"}),
            ],
            edges=[
                GraphEdge(edge_id="e1", source_node="10.2.28.88", target_node="45.131.214.85", first_seen="2026-05-31T00:00:01Z", relationship_risk=80.0)
            ],
        )

    def _hypothesis(self):
        return AttackHypothesis(
            hypothesis_id="h1",
            hypothesis_type="beaconing",
            title="Beaconing",
            summary="Beaconing: 10.2.28.88 to 45.131.214.85",
            impacted_entities=["10.2.28.88", "45.131.214.85"],
            supporting_evidence=["periodicity", "rare_destination", "exclusive_destination"],
            confidence=92.0,
            severity="high",
            created_at="2026-05-31T00:01:00Z",
        )

    def _candidate(self):
        hypothesis = self._hypothesis()
        return InvestigationCandidate(
            host="10.2.28.88",
            host_role="WORKSTATION",
            priority="HIGH",
            priority_score=83.0,
            confidence=92.0,
            risk=74.0,
            findings=[hypothesis],
            hypotheses=[hypothesis],
        )


if __name__ == "__main__":
    unittest.main()
