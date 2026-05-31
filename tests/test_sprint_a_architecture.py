import types
import unittest

from behavior.node_filters import is_non_investigative_node
from behavior.role_manager import infer_host_role
from behavior.schemas import GraphNode
from graph.community_classifier import classify_community, classify_graph_nodes
from layer5.engine import Layer5Phase1Engine, compute_priority_score
from layer5.schemas import AttackHypothesis


class TestSprintAArchitecture(unittest.TestCase):
    def test_domain_controller_role(self):
        role = infer_host_role(
            {
                "protocols": ["dns", "kerberos", "ldap", "smb", "msrpc"],
                "inbound_ratio": 0.55,
                "responded_flow_count": 80,
                "unique_destinations": 5,
                "internal_unique_hosts": 20,
                "persistent_relationships": 2,
            },
            {"service_ports": {53, 88, 389, 445}},
            "10.0.0.10",
        )

        self.assertEqual(role["role"], "DOMAIN_CONTROLLER")
        self.assertGreaterEqual(role["confidence"], 0.8)

    def test_workstation_role(self):
        role = infer_host_role(
            {
                "protocols": ["dns", "https", "http"],
                "outbound_ratio": 0.82,
                "inbound_ratio": 0.05,
                "responded_flow_count": 2,
                "unique_destinations": 18,
                "internal_unique_hosts": 3,
                "persistent_relationships": 1,
            },
            {"service_ports": set()},
            "10.0.0.20",
        )

        self.assertEqual(role["role"], "WORKSTATION")
        self.assertGreaterEqual(role["confidence"], 0.8)

    def test_external_service_role(self):
        role = infer_host_role(
            {
                "protocols": ["https"],
                "internal_unique_hosts": 12,
                "persistent_relationships": 4,
            },
            {"service_ports": {443}},
            "45.131.214.85",
        )

        self.assertEqual(role["role"], "EXTERNAL_SERVICE")

    def test_workstation_community(self):
        community, confidence = classify_community("WORKSTATION")

        self.assertEqual(community, "Workstations")
        self.assertGreater(confidence, 0.8)

    def test_server_community(self):
        community, _ = classify_community("SERVER")

        self.assertEqual(community, "Servers")

    def test_external_service_community(self):
        community, _ = classify_community("EXTERNAL_SERVICE")

        self.assertEqual(community, "External Services")

    def test_all_graph_nodes_classified(self):
        nodes = [
            self._graph_node("10.2.28.88", "WORKSTATION"),
            self._graph_node("10.2.28.2", "INFRASTRUCTURE"),
            self._graph_node("45.131.214.85", "EXTERNAL_SERVICE"),
            self._graph_node("10.2.28.255", "UNKNOWN"),
        ]

        communities = classify_graph_nodes(nodes, [])
        classified_count = sum(len(hosts) for hosts in communities.values())

        self.assertEqual(classified_count, len(nodes))

    def test_percentage_total(self):
        nodes = [
            self._graph_node("10.2.28.88", "WORKSTATION"),
            self._graph_node("10.2.28.89", "WORKSTATION"),
            self._graph_node("10.2.28.2", "INFRASTRUCTURE"),
            self._graph_node("45.131.214.85", "EXTERNAL_SERVICE"),
        ]

        communities = classify_graph_nodes(nodes, [])
        total = sum(len(hosts) for hosts in communities.values())
        percentages = [len(hosts) / total * 100 for hosts in communities.values()]

        self.assertAlmostEqual(sum(percentages), 100.0)

    def test_workstation_population(self):
        nodes = [
            self._graph_node("10.2.28.88", "WORKSTATION"),
            self._graph_node("10.2.28.89", "WORKSTATION"),
            self._graph_node("10.2.28.90", "WORKSTATION"),
            self._graph_node("45.131.214.85", "EXTERNAL_SERVICE"),
        ]

        communities = classify_graph_nodes(nodes, [])

        self.assertGreater(len(communities["Workstations"]), 1)

    def test_domain_controller_presence(self):
        node = self._graph_node("10.2.28.2", "INFRASTRUCTURE")
        communities = classify_graph_nodes([node], [])

        self.assertIn("10.2.28.2", communities["Infrastructure"])

    def test_broadcast_suppressed(self):
        self.assertTrue(is_non_investigative_node("10.2.28.255"))
        self.assertTrue(is_non_investigative_node("255.255.255.255"))

    def test_multicast_suppressed(self):
        self.assertTrue(is_non_investigative_node("224.0.0.251"))

    def test_hypothesis_contradictions(self):
        hypothesis = AttackHypothesis(
            hypothesis_id="h1",
            hypothesis_type="beaconing",
            title="Beaconing",
            summary="Cloud endpoint beaconing.",
            impacted_entities=["10.2.28.88", "104.208.203.89"],
            supporting_evidence=["periodicity", "persistence"],
            contradictory_evidence=["common_cloud_service"],
            confidence=74.0,
            severity="low",
            created_at="2026-05-31T00:00:00Z",
        )

        self.assertEqual(hypothesis.contradictory_evidence, ["common_cloud_service"])

    def test_candidate_does_not_merge_contradictions(self):
        engine = Layer5Phase1Engine()
        profiles = {
            "10.2.28.88": types.SimpleNamespace(
                risk_score=74.0,
                role="WORKSTATION",
                role_confidence=0.84,
                external_unique_hosts=95,
                internal_unique_hosts=4,
                protocols=["dns", "https", "smb"],
            )
        }
        primary = AttackHypothesis(
            hypothesis_id="h1",
            hypothesis_type="beaconing",
            title="Beaconing",
            summary="Rare endpoint beaconing.",
            impacted_entities=["10.2.28.88", "45.131.214.85"],
            supporting_evidence=["periodicity", "rare_destination"],
            contradictory_evidence=[],
            confidence=92.0,
            severity="high",
            priority_score=73.1,
            created_at="2026-05-31T00:00:00Z",
            metadata={"relationship_consumer": "10.2.28.88", "relationship_destination": "45.131.214.85"},
        )
        secondary = AttackHypothesis(
            hypothesis_id="h2",
            hypothesis_type="beaconing",
            title="Beaconing",
            summary="Cloud endpoint beaconing.",
            impacted_entities=["10.2.28.88", "104.208.203.89"],
            supporting_evidence=["periodicity"],
            contradictory_evidence=["common_cloud_service"],
            confidence=74.0,
            severity="low",
            priority_score=66.8,
            created_at="2026-05-31T00:00:00Z",
            metadata={"relationship_consumer": "10.2.28.88", "relationship_destination": "104.208.203.89"},
        )

        candidate = engine.build_investigation_candidates([primary, secondary], profiles)[0]
        candidate_document = candidate.model_dump()

        self.assertNotIn("contradictory_evidence", candidate_document)
        self.assertEqual(candidate.hypotheses[0].contradictory_evidence, [])
        self.assertEqual(candidate.hypotheses[1].contradictory_evidence, ["common_cloud_service"])

    def test_priority_score_calculation(self):
        self.assertEqual(compute_priority_score(80.0, 70.0, 100.0), 82.5)

    def test_priority_level_assignment(self):
        engine = Layer5Phase1Engine()

        self.assertEqual(engine._priority_level(91.0), "CRITICAL")
        self.assertEqual(engine._priority_level(76.0), "HIGH")
        self.assertEqual(engine._priority_level(61.0), "MEDIUM")
        self.assertEqual(engine._priority_level(41.0), "LOW")
        self.assertEqual(engine._priority_level(20.0), "INFORMATIONAL")

    def _graph_node(self, ip_address: str, role: str) -> GraphNode:
        return GraphNode(
            node_id=ip_address,
            ip_address=ip_address,
            inferred_role=role,
            role=role,
        )


if __name__ == "__main__":
    unittest.main()
