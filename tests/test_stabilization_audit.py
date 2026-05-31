import json
import tempfile
import types
import unittest

from behavior.schemas import GraphNode, GraphState, TemporalSnapshot
from layer5.schemas import AttackHypothesis, InvestigationCandidate
from stabilization_audit import write_stabilization_exports


class TestStabilizationAudit(unittest.TestCase):
    def test_stabilization_exports_validate_consistent_state(self):
        graph_state = GraphState(
            snapshot_id="snapshot",
            timestamp="2026-05-31T00:00:00Z",
            node_count=2,
            nodes=[
                GraphNode(
                    node_id="n1",
                    ip_address="10.2.28.88",
                    role="WORKSTATION",
                    inferred_role="WORKSTATION",
                    risk_score=74.0,
                    metadata={"role_confidence": 0.84, "community_type": "Workstations"},
                ),
                GraphNode(
                    node_id="n2",
                    ip_address="45.131.214.85",
                    role="EXTERNAL_SERVICE",
                    inferred_role="EXTERNAL_SERVICE",
                    risk_score=55.0,
                    metadata={"role_confidence": 0.82, "community_type": "External Services"},
                ),
            ],
            metadata={
                "communities": {
                    "Workstations": ["10.2.28.88"],
                    "External Services": ["45.131.214.85"],
                },
            },
        )
        hypothesis = AttackHypothesis(
            hypothesis_id="h1",
            hypothesis_type="beaconing",
            title="Beaconing",
            summary="Beaconing",
            impacted_entities=["10.2.28.88", "45.131.214.85"],
            supporting_evidence=["periodicity"],
            contradictory_evidence=[],
            confidence_explanation="Confidence 92%.",
            confidence=92.0,
            created_at="2026-05-31T00:00:00Z",
        )
        candidate = InvestigationCandidate(
            host="10.2.28.88",
            host_role="WORKSTATION",
            priority="MEDIUM",
            priority_score=73.1,
            priority_explanation={"priority_score": 73.1},
            risk=74.0,
            findings=[hypothesis],
        )
        snapshots = [
            TemporalSnapshot(
                snapshot_id="s1",
                window_start="2026-05-31T00:00:00Z",
                window_end="2026-05-31T00:01:00Z",
                metadata={"quality_score": 1.0, "quality_reason": "useful_snapshot"},
            )
        ]
        profiles = [
            types.SimpleNamespace(ip_address="10.2.28.88", role="WORKSTATION"),
            types.SimpleNamespace(ip_address="45.131.214.85", role="EXTERNAL_SERVICE"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            report = write_stabilization_exports(
                host_profiles=profiles,
                graph_state=graph_state,
                hypotheses=[hypothesis],
                investigation_candidates=[candidate],
                temporal_snapshots=snapshots,
                output_dir=tmpdir,
            )

            self.assertTrue(report["stable"])
            self.assertEqual(report["graph_consistency"]["graph_nodes"], 2)
            self.assertEqual(report["graph_consistency"]["classified_nodes"], 2)
            with open(f"{tmpdir}/layer6_readiness.json", encoding="utf-8") as stream:
                readiness = json.load(stream)
            self.assertTrue(readiness["ready"])


if __name__ == "__main__":
    unittest.main()
