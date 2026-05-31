import os
import tempfile
import types
import unittest

from layer5.delta import detect_host_deltas, detect_relationship_deltas
from layer5.engine import Layer5Phase1Engine, compute_priority_score
from layer5.exports import export_ndjson
from layer5.hypotheses import compute_destination_exclusivity, compute_destination_rarity, deduplicate_evidence
from layer5.registry import HypothesisRegistry
from layer5.schemas import BehavioralDelta


class TestLayer5Phase1(unittest.TestCase):
    def test_detect_host_deltas(self):
        previous = types.SimpleNamespace(
            ip_address="10.0.0.1",
            risk_score=10.0,
            unique_ports=4,
            protocol_relationships=4,
            unique_peers=3,
            external_unique_hosts=1,
            persistent_relationships=2,
            persistent_connection_ratio=0.15,
            protocols=["http"],
        )
        current = types.SimpleNamespace(
            ip_address="10.0.0.1",
            risk_score=40.0,
            unique_ports=9,
            protocol_relationships=12,
            unique_peers=8,
            external_unique_hosts=4,
            persistent_relationships=1,
            persistent_connection_ratio=0.45,
            protocols=["http", "https"],
        )

        deltas = detect_host_deltas([current], [previous])
        delta_types = {delta.delta_type for delta in deltas}
        self.assertIn("risk_increase", delta_types)
        self.assertIn("protocol_change", delta_types)
        self.assertIn("persistence_change", delta_types)
        self.assertIn("host_behavior_change", delta_types)

    def test_detect_relationship_deltas(self):
        previous = types.SimpleNamespace(
            edge_id="edge01",
            source="10.0.0.1",
            target="10.0.0.2",
            protocols=["http"],
            persistence=0.10,
        )
        current = types.SimpleNamespace(
            edge_id="edge01",
            source="10.0.0.1",
            target="10.0.0.2",
            protocols=["https"],
            persistence=0.45,
        )
        new_external = types.SimpleNamespace(
            edge_id="edge02",
            source="10.0.0.1",
            target="8.8.8.8",
            protocols=["https"],
            persistence=0.50,
        )

        deltas = detect_relationship_deltas([current, new_external], [previous])
        delta_types = {delta.delta_type for delta in deltas}
        self.assertIn("persistence_increase", delta_types)
        self.assertIn("protocol_evolution", delta_types)
        self.assertIn("external_relationship_emergence", delta_types)

    def test_hypothesis_evaluation(self):
        registry = HypothesisRegistry()
        engine = Layer5Phase1Engine(registry=registry)

        host_delta = BehavioralDelta(
            delta_id="delta-host-1",
            entity_type="host",
            delta_type="host_behavior_change",
            entity_id="10.0.0.1",
            detected_at="2026-05-31T00:00:00Z",
            confidence=0.7,
            severity="informational",
            summary="Host behavior change sample.",
            metrics={
                "new_relationship_count": 8,
                "unique_ports_delta": 6,
                "external_host_delta": 3,
                "same_port_peer_count": 1.0,
                "low_persistence_ratio": 1.0,
                "risk_score_delta": 18.0,
            },
        )
        relationship_delta = BehavioralDelta(
            delta_id="delta-rel-1",
            entity_type="relationship",
            delta_type="external_relationship_emergence",
            entity_id="edge01",
            detected_at="2026-05-31T00:00:00Z",
            confidence=0.8,
            severity="medium",
            summary="Relationship persistence increased.",
            metrics={
                "source": "10.0.0.1",
                "target": "8.8.8.8",
                "protocols": ["https"],
                "persistence": 0.68,
            },
        )
        relationship_delta_persistent = BehavioralDelta(
            delta_id="delta-rel-2",
            entity_type="relationship",
            delta_type="persistence_increase",
            entity_id="edge02",
            detected_at="2026-05-31T00:00:00Z",
            confidence=0.8,
            severity="medium",
            summary="Relationship persistence increased.",
            metrics={
                "source": "10.0.0.2",
                "target": "8.8.8.9",
                "protocols": ["https"],
                "persistence": 0.75,
            },
        )

        hypotheses = engine.evaluate([host_delta], [relationship_delta, relationship_delta_persistent])
        hypothesis_types = {hypothesis.hypothesis_type for hypothesis in hypotheses}
        self.assertIn("port_scan", hypothesis_types)
        self.assertIn("host_sweep", hypothesis_types)
        self.assertIn("beaconing", hypothesis_types)
        self.assertIn("persistent_tls", hypothesis_types)

    def test_destination_rarity_and_candidate_ranking(self):
        engine = Layer5Phase1Engine()
        host_profiles = {
            "10.2.28.88": types.SimpleNamespace(risk_score=74.0, role="WORKSTATION", role_confidence=0.84, external_unique_hosts=95, internal_unique_hosts=4, protocols=["dns", "https", "smb"]),
            "10.2.28.89": types.SimpleNamespace(risk_score=20.0, role="WORKSTATION", role_confidence=0.70, external_unique_hosts=2, internal_unique_hosts=1, protocols=["dns", "https"]),
        }
        rare_destination = BehavioralDelta(
            delta_id="rare-beacon",
            entity_type="relationship",
            delta_type="external_relationship_emergence",
            entity_id="edge-rare",
            detected_at="2026-05-31T00:00:00Z",
            confidence=0.8,
            severity="medium",
            summary="Rare external TLS relationship.",
            metrics={
                "source": "10.2.28.88",
                "target": "45.131.214.85",
                "protocols": ["https"],
                "persistence": 0.68,
                "flows": 3,
            },
        )
        common_cloud = BehavioralDelta(
            delta_id="cloud-beacon",
            entity_type="relationship",
            delta_type="external_relationship_emergence",
            entity_id="edge-cloud",
            detected_at="2026-05-31T00:00:00Z",
            confidence=0.8,
            severity="medium",
            summary="Common cloud TLS relationship.",
            metrics={
                "source": "10.2.28.88",
                "target": "104.208.203.89",
                "protocols": ["https"],
                "persistence": 0.68,
                "flows": 3,
            },
        )
        shared_cloud = BehavioralDelta(
            delta_id="shared-cloud",
            entity_type="relationship",
            delta_type="external_relationship_emergence",
            entity_id="edge-shared-cloud",
            detected_at="2026-05-31T00:00:00Z",
            confidence=0.8,
            severity="medium",
            summary="Second consumer for cloud endpoint.",
            metrics={
                "source": "10.2.28.89",
                "target": "104.208.203.89",
                "protocols": ["https"],
                "persistence": 0.68,
                "flows": 3,
            },
        )

        hypotheses = engine.evaluate([], [rare_destination, common_cloud, shared_cloud], host_profiles)
        beaconing = [hypothesis for hypothesis in hypotheses if hypothesis.hypothesis_type == "beaconing"]

        self.assertGreaterEqual(len(beaconing), 2)
        self.assertEqual(beaconing[0].metadata["relationship_destination"], "45.131.214.85")
        self.assertGreater(
            beaconing[0].confidence,
            next(
                hypothesis.confidence
                for hypothesis in beaconing
                if hypothesis.metadata["relationship_destination"] == "104.208.203.89"
            ),
        )
        self.assertIn("common_cloud_service", beaconing[-1].contradictory_evidence)
        self.assertIn("Confidence", beaconing[0].confidence_explanation)

        candidates = engine.build_investigation_candidates(hypotheses, host_profiles)
        self.assertEqual(candidates[0].host, "10.2.28.88")
        self.assertGreater(candidates[0].confidence, 0.0)
        self.assertNotIn("supporting_evidence", candidates[0].model_dump())
        self.assertNotIn("contradictory_evidence", candidates[0].model_dump())
        self.assertIn("findings", candidates[0].narrative_context)
        self.assertIn("rare and exclusive external destination", candidates[0].candidate_rationale)
        self.assertEqual(candidates[0].host_summary["host_role"], "Workstation")

        rare_finding = next(
            hypothesis
            for hypothesis in beaconing
            if hypothesis.metadata["relationship_destination"] == "45.131.214.85"
        )
        cloud_finding = next(
            hypothesis
            for hypothesis in beaconing
            if hypothesis.metadata["relationship_destination"] == "104.208.203.89"
        )
        self.assertEqual(rare_finding.finding_tier, "PRIMARY")
        self.assertIn(cloud_finding.finding_tier, {"SECONDARY", "SUPPORTING"})
        self.assertIn("common_cloud_service", cloud_finding.confidence_explanation)
        self.assertNotIn("no contradictory evidence", cloud_finding.confidence_explanation)

    def test_destination_scoring_helpers(self):
        self.assertEqual(compute_destination_rarity(1), 1.0)
        self.assertEqual(compute_destination_rarity(50), 0.02)
        self.assertEqual(compute_destination_exclusivity(1), 1.0)
        self.assertLess(compute_destination_exclusivity(50), 0.1)

    def test_evidence_deduplication_preserves_order(self):
        self.assertEqual(
            deduplicate_evidence([" periodicity ", "Periodicity", "persistence", "", "PERSISTENCE"]),
            ["periodicity", "persistence"],
        )

    def test_priority_score_calculation(self):
        self.assertEqual(compute_priority_score(74.0, 92.0, 50.0), 73.1)

    def test_ndjson_export(self):
        hypothesis = BehavioralDelta(
            delta_id="delta-host-2",
            entity_type="host",
            delta_type="new_host",
            entity_id="10.0.0.2",
            detected_at="2026-05-31T00:00:00Z",
            confidence=0.75,
            severity="informational",
            summary="Host appears.",
            metrics={"current_unique_ports": 3},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "deltas.ndjson")
            export_ndjson([hypothesis], output_path)
            with open(output_path, "r", encoding="utf-8") as stream:
                lines = stream.readlines()
            self.assertEqual(len(lines), 1)
            self.assertIn("new_host", lines[0])


if __name__ == "__main__":
    unittest.main()
