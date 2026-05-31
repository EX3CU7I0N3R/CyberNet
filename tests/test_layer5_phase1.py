import os
import tempfile
import types
import unittest

from layer5.delta import detect_host_deltas, detect_relationship_deltas
from layer5.engine import Layer5Phase1Engine
from layer5.exports import export_ndjson
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
