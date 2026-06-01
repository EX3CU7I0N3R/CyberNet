import json
import tempfile
import unittest
from pathlib import Path

from layer8_backend import ReplayService
from layer8_backend.websocket import ReplayWebSocketController


class TestLayer8Backend(unittest.TestCase):
    def test_session_creation(self):
        with self._artifact_dir() as artifact_dir:
            session = ReplayService(str(artifact_dir)).create_session()

        self.assertEqual(session.frame_count, 3)
        self.assertEqual(session.duration, 20.0)
        self.assertTrue(session.session_id)

    def test_frame_query(self):
        with self._artifact_dir() as artifact_dir:
            frame = ReplayService(str(artifact_dir)).get_frame(2)

        self.assertEqual(frame.frame_id, 2)
        self.assertEqual(frame.frame_key, "frame_00002")
        self.assertEqual(frame.nodes[0]["ip"], "10.2.28.88")
        self.assertIn("node_count", frame.graph_metrics)

    def test_seek_returns_nearest_frame(self):
        with self._artifact_dir() as artifact_dir:
            frame = ReplayService(str(artifact_dir)).seek("2026-05-31T00:00:11Z")

        self.assertEqual(frame.frame_id, 2)

    def test_chapters_events_narratives_and_host_details(self):
        with self._artifact_dir() as artifact_dir:
            service = ReplayService(str(artifact_dir))
            chapters = service.chapters()
            events = service.events()
            narratives = service.narratives()
            host = service.host("10.2.28.88")

        self.assertEqual(chapters[0].title, "Initial Network Activity")
        self.assertEqual(events[0].type, "host_role_assigned")
        self.assertEqual(narratives[0].host, "10.2.28.88")
        self.assertEqual(host.risk, 74.0)
        self.assertEqual(host.role, "WORKSTATION")
        self.assertEqual(host.hostname, "DESKTOP-ES9F3ML")
        self.assertEqual(host.mac_address, "00:21:5d:c8:0e:f2")
        self.assertEqual(host.user_identity, "gwyatt")
        self.assertTrue(host.storyline)

    def test_chapter_jump_uses_chapter_start_time(self):
        with self._artifact_dir() as artifact_dir:
            frame = ReplayService(str(artifact_dir)).chapter_jump(2)

        self.assertEqual(frame.timestamp, "2026-05-31T00:00:20Z")

    def test_websocket_controller_commands(self):
        with self._artifact_dir() as artifact_dir:
            service = ReplayService(str(artifact_dir))
            controller = ReplayWebSocketController(service)
            play_state = controller.handle({"action": "play"})
            speed_state = controller.handle({"action": "speed", "value": 8})
            seek_state = controller.handle({"action": "seek", "frame": 2})

        self.assertTrue(play_state["playing"])
        self.assertEqual(speed_state["speed"], 8)
        self.assertEqual(seek_state["replay_frame"]["frame_id"], 2)

    def test_summary_context(self):
        with self._artifact_dir() as artifact_dir:
            summary = ReplayService(str(artifact_dir)).summary()

        self.assertEqual(summary.frame_count, 3)
        self.assertEqual(summary.event_count, 2)
        self.assertEqual(summary.hypothesis_count, 1)
        self.assertEqual(summary.candidate_count, 1)
        self.assertEqual(summary.top_host, "10.2.28.88")
        self.assertEqual(summary.primary_destination, "45.131.214.85")

    def test_ranked_hosts(self):
        with self._artifact_dir() as artifact_dir:
            hosts = ReplayService(str(artifact_dir)).ranked_hosts()

        self.assertEqual(hosts[0].ip, "10.2.28.88")
        self.assertEqual(hosts[0].role, "WORKSTATION")
        self.assertEqual(hosts[0].candidate_status, "candidate")
        self.assertEqual(hosts[0].finding_count, 1)
        self.assertEqual(hosts[0].hostname, "DESKTOP-ES9F3ML")
        self.assertEqual(hosts[0].mac_address, "00:21:5d:c8:0e:f2")
        self.assertEqual(hosts[0].user_identity, "gwyatt")

    def test_hypotheses_context(self):
        with self._artifact_dir() as artifact_dir:
            hypotheses = ReplayService(str(artifact_dir)).hypotheses()

        self.assertEqual(hypotheses[0].supporting_evidence, ["rare_destination"])
        self.assertEqual(hypotheses[0].contradictory_evidence, [])
        self.assertIn("Confidence", hypotheses[0].confidence_explanation)
        self.assertEqual(hypotheses[0].metadata["destination_rarity_score"], 1.0)

    def test_candidates_context(self):
        with self._artifact_dir() as artifact_dir:
            candidates = ReplayService(str(artifact_dir)).candidates()

        self.assertEqual(candidates[0].priority_explanation["priority_score"], 73.0)
        self.assertEqual(candidates[0].recommended_actions, ["inspect endpoint"])

    def test_relationships_for_host(self):
        with self._artifact_dir() as artifact_dir:
            relationships = ReplayService(str(artifact_dir)).relationships("10.2.28.88")

        self.assertEqual(relationships[0].target, "45.131.214.85")
        self.assertEqual(relationships[0].destination_consumer_count, 1)

    def test_destinations_context(self):
        with self._artifact_dir() as artifact_dir:
            destinations = ReplayService(str(artifact_dir)).destinations()

        self.assertEqual(destinations[0].ip, "45.131.214.85")
        self.assertEqual(destinations[0].consumer_count, 1)
        self.assertEqual(destinations[0].rarity_score, 1.0)

    def test_community_context(self):
        with self._artifact_dir() as artifact_dir:
            community = ReplayService(str(artifact_dir)).community()

        self.assertEqual(community.graph_nodes, community.classified_nodes)
        self.assertEqual(community.community_distribution["Workstations"], 1)

    def test_artifact_health(self):
        with self._artifact_dir() as artifact_dir:
            health = ReplayService(str(artifact_dir)).artifact_health()

        self.assertTrue(health.graph_consistency["valid"])
        self.assertTrue(health.hypothesis_validation["valid"])
        self.assertTrue(health.layer6_readiness["ready"])

    def test_empty_artifact_directory_is_valid_pre_capture_state(self):
        with tempfile.TemporaryDirectory() as artifact_dir:
            service = ReplayService(artifact_dir)
            session = service.create_session()

            self.assertEqual(session.frame_count, 0)
            self.assertEqual(session.duration, 0.0)
            self.assertEqual(service.events(), [])
            self.assertEqual(service.candidates(), [])
            self.assertEqual(service.summary().frame_count, 0)
            self.assertEqual(service.summary().top_host, None)

    def test_runtime_logs(self):
        with self._artifact_dir() as artifact_dir:
            (Path(artifact_dir) / "layer8_backend.stderr.log").write_text("line one\nline two\n", encoding="utf-8")
            logs = ReplayService(str(artifact_dir)).runtime_logs(lines=1)

        self.assertEqual(logs["stderr"], ["line two"])
        self.assertIn("health", logs)

    def test_clear_artifacts_preserves_uploads_and_backend_logs(self):
        with self._artifact_dir() as artifact_dir:
            artifact_path = Path(artifact_dir)
            (artifact_path / "temporary_artifact.txt").write_text("stale", encoding="utf-8")
            (artifact_path / "uploads").mkdir()
            (artifact_path / "uploads" / "capture.pcap").write_text("pcap", encoding="utf-8")
            (artifact_path / "layer8_backend.stdout.log").write_text("server log", encoding="utf-8")

            clear_result = ReplayService(str(artifact_dir)).clear_artifacts()

            self.assertIn("temporary_artifact.txt", clear_result["cleared"])
            self.assertFalse((artifact_path / "temporary_artifact.txt").exists())
            self.assertTrue((artifact_path / "uploads" / "capture.pcap").exists())
            self.assertTrue((artifact_path / "layer8_backend.stdout.log").exists())

    def test_context_fallback_when_layer5_is_empty(self):
        with self._artifact_dir() as artifact_dir:
            artifact_path = Path(artifact_dir)
            (artifact_path / "layer5_hypotheses.ndjson").write_text("", encoding="utf-8")
            (artifact_path / "layer5_investigation_candidates.ndjson").write_text("", encoding="utf-8")
            self._write_ndjson(
                artifact_path / "enriched_flows.ndjson",
                [
                    {
                        "flow_id": "flow1",
                        "direction": "outbound",
                        "application_protocol": "http",
                        "initiator_ip": "10.1.21.58",
                        "responder_ip": "153.92.1.49",
                        "responder_port": 80,
                        "packet_count": 42,
                        "observed_domains": ["whitepepper.su"],
                    }
                ],
            )
            self._write_ndjson(
                artifact_path / "host_profiles.ndjson",
                [
                    {
                        "ip_address": "10.1.21.58",
                        "role": "WORKSTATION",
                        "role_confidence": 0.82,
                        "risk_score": 64.0,
                        "mac_address": "00:21:5d:c8:0e:f2",
                        "hostname": "DESKTOP-ES9F3ML",
                        "user_identity": "gwyatt",
                        "external_unique_relationships": 3,
                        "internal_unique_relationships": 1,
                        "protocols": ["http", "https"],
                        "metadata": {"community_type": "Workstations"},
                    }
                ],
            )

            service = ReplayService(str(artifact_path))
            summary = service.summary()
            candidates = service.candidates()
            hypotheses = service.hypotheses()

        self.assertEqual(summary.top_host, "10.1.21.58")
        self.assertEqual(summary.primary_destination, "153.92.1.49")
        self.assertEqual(candidates[0].host, "10.1.21.58")
        self.assertEqual(candidates[0].host_summary["hostname"], "DESKTOP-ES9F3ML")
        self.assertEqual(hypotheses[0].metadata["domain"], "whitepepper.su")
        self.assertIn("domain_observed:whitepepper.su", hypotheses[0].supporting_evidence)

    def _artifact_dir(self):
        temp_dir = tempfile.TemporaryDirectory()
        artifact_dir = Path(temp_dir.name)
        self._write_ndjson(artifact_dir / "replay_frames.ndjson", self._frames())
        self._write_ndjson(artifact_dir / "timeline_events.ndjson", self._events())
        self._write_ndjson(artifact_dir / "activity_phases.ndjson", self._phases())
        self._write_ndjson(artifact_dir / "major_chapters.ndjson", self._chapters())
        self._write_ndjson(artifact_dir / "host_timelines.ndjson", self._host_timelines())
        self._write_ndjson(artifact_dir / "investigation_narratives.ndjson", self._narratives())
        self._write_ndjson(artifact_dir / "layer5_hypotheses.ndjson", self._hypotheses())
        self._write_ndjson(artifact_dir / "layer5_investigation_candidates.ndjson", self._candidates())
        self._write_ndjson(artifact_dir / "relationships.ndjson", self._relationships())
        self._write_ndjson(artifact_dir / "host_profiles.ndjson", self._host_profiles())
        self._write_json(artifact_dir / "graph_consistency.json", self._graph_consistency())
        self._write_json(artifact_dir / "hypothesis_validation.json", {"valid": True})
        self._write_json(artifact_dir / "investigation_candidate_validation.json", {"valid": True})
        self._write_json(artifact_dir / "snapshot_quality.json", {"valid": True, "quality_score": 1.0})
        self._write_json(artifact_dir / "role_consistency_report.json", {"valid": True, "mismatches": []})
        self._write_json(artifact_dir / "layer6_readiness.json", {"ready": True, "missing_components": []})
        self._write_csv(artifact_dir / "community_audit.csv")
        return temp_dir

    def _write_ndjson(self, path, rows):
        with path.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row) + "\n")

    def _write_json(self, path, row):
        path.write_text(json.dumps(row), encoding="utf-8")

    def _write_csv(self, path):
        path.write_text(
            "ip,role,role_confidence,community,is_internal,is_external,risk_score\n"
            "10.2.28.88,WORKSTATION,84.0,Workstations,True,False,74.0\n"
            "45.131.214.85,EXTERNAL_SERVICE,92.0,External Services,False,True,55.0\n",
            encoding="utf-8",
        )

    def _frames(self):
        return [
            self._frame("frame_00001", "2026-05-31T00:00:00Z", []),
            self._frame("frame_00002", "2026-05-31T00:00:10Z", [{"event_id": "e2"}]),
            self._frame("frame_00003", "2026-05-31T00:00:20Z", [{"event_id": "e3"}]),
        ]

    def _frame(self, frame_id, timestamp, events):
        return {
            "frame_id": frame_id,
            "timestamp": timestamp,
            "state": {
                "timestamp": timestamp,
                "nodes": [
                    {"id": "n1", "ip": "10.2.28.88", "risk_score": 74.0, "role": "WORKSTATION"}
                ],
                "edges": [
                    {"id": "edge1", "source": "n1", "target": "n2", "relationship_type": "external_tls_session"}
                ],
                "events": events,
                "candidate_hosts": [{"host": "10.2.28.88", "priority": "HIGH"}],
                "graph_metrics": {"node_count": 1, "edge_count": 1},
            },
            "delta": {"new_events": events},
            "frame_duration": 10.0,
            "timestamp_delta": 10.0,
        }

    def _events(self):
        return [
            {
                "event_id": "e1",
                "timestamp": "2026-05-31T00:00:00Z",
                "event_type": "host_role_assigned",
                "severity": "INFO",
                "host": "10.2.28.88",
                "related_hosts": [],
                "description": "role assigned",
                "metadata": {"role": "WORKSTATION"},
            },
            {
                "event_id": "e2",
                "timestamp": "2026-05-31T00:00:10Z",
                "event_type": "tls_established",
                "severity": "MEDIUM",
                "host": "10.2.28.88",
                "related_hosts": ["45.131.214.85"],
                "description": "tls",
                "metadata": {},
            },
        ]

    def _phases(self):
        return [
            {
                "phase_id": "p1",
                "phase_name": "Communication",
                "start_time": "2026-05-31T00:00:00Z",
                "end_time": "2026-05-31T00:00:20Z",
                "events": ["e1", "e2"],
                "description": "phase",
            }
        ]

    def _chapters(self):
        return [
            {
                "chapter_id": "c1",
                "chapter_type": "INITIAL_ACTIVITY",
                "title": "Initial Network Activity",
                "description": "initial",
                "start_time": "2026-05-31T00:00:00Z",
                "end_time": "2026-05-31T00:00:10Z",
                "hosts": ["10.2.28.88"],
                "key_events": ["host_role_assigned"],
                "importance": 30,
            },
            {
                "chapter_id": "c2",
                "chapter_type": "EXTERNAL_COMMUNICATION",
                "title": "External Communication",
                "description": "external",
                "start_time": "2026-05-31T00:00:20Z",
                "end_time": "2026-05-31T00:00:20Z",
                "hosts": ["10.2.28.88"],
                "key_events": ["tls_established"],
                "importance": 75,
            },
        ]

    def _host_timelines(self):
        return [
            {
                "host": "10.2.28.88",
                "events": [{"event_id": "e1"}, {"event_id": "e2"}],
                "chapters": [{"chapter_id": "c1", "title": "Initial Network Activity"}],
            }
        ]

    def _narratives(self):
        return [
            {
                "host": "10.2.28.88",
                "priority": "HIGH",
                "confidence": 92.0,
                "executive_summary": "summary",
                "behavioral_summary": "behavior",
                "assessment": "assessment",
                "recommended_actions": ["Review endpoint telemetry"],
                "investigation_plan": ["Review endpoint telemetry"],
            }
        ]

    def _hypotheses(self):
        return [
            {
                "hypothesis_id": "h1",
                "hypothesis_type": "beaconing",
                "title": "Beaconing",
                "summary": "TLS beaconing: 10.2.28.88 <-> 45.131.214.85",
                "impacted_entities": ["10.2.28.88", "45.131.214.85"],
                "supporting_evidence": ["rare_destination"],
                "contradictory_evidence": [],
                "confidence_explanation": "Confidence 92%. Positive: + rare destination. Negative: - none observed.",
                "confidence": 92.0,
                "severity": "high",
                "priority_score": 73.0,
                "priority_level": "MEDIUM",
                "finding_tier": "PRIMARY",
                "metadata": {
                    "relationship_consumer": "10.2.28.88",
                    "relationship_destination": "45.131.214.85",
                    "destination_consumer_count": 1,
                    "destination_rarity_score": 1.0,
                    "destination_exclusivity_score": 1.0,
                },
            }
        ]

    def _candidates(self):
        return [
            {
                "host": "10.2.28.88",
                "host_role": "WORKSTATION",
                "priority": "MEDIUM",
                "priority_score": 73.0,
                "priority_explanation": {"priority_score": 73.0},
                "confidence": 92.0,
                "risk": 74.0,
                "candidate_rationale": "rare destination",
                "host_summary": {
                    "role_confidence": 0.84,
                    "external_relationships": 1,
                    "internal_relationships": 0,
                    "top_protocols": ["https"],
                },
                "rationale": ["rare_destination"],
                "recommended_actions": ["inspect endpoint"],
                "narrative_context": {"findings": self._hypotheses()},
            }
        ]

    def _relationships(self):
        return [
            {
                "edge_id": "r1",
                "source": "10.2.28.88",
                "target": "45.131.214.85",
                "relationship_risk": 55.0,
                "confidence": 0.9,
                "severity": "high",
                "protocols": ["https"],
                "first_seen": "2026-05-31T00:00:00Z",
                "last_seen": "2026-05-31T00:00:20Z",
            }
        ]

    def _host_profiles(self):
        return [
            {
                "ip_address": "10.2.28.88",
                "role": "WORKSTATION",
                "role_confidence": 0.84,
                "risk_score": 74.0,
                "mac_address": "00:21:5d:c8:0e:f2",
                "hostname": "DESKTOP-ES9F3ML",
                "user_identity": "gwyatt",
                "external_unique_relationships": 1,
                "internal_unique_relationships": 0,
                "protocols": ["https"],
                "metadata": {"community_type": "Workstations"},
            }
        ]

    def _graph_consistency(self):
        return {
            "graph_nodes": 2,
            "classified_nodes": 2,
            "unclassified_nodes": 0,
            "community_distribution": {"Workstations": 1, "External Services": 1},
            "role_count": {"WORKSTATION": 1, "EXTERNAL_SERVICE": 1},
            "valid": True,
        }


if __name__ == "__main__":
    unittest.main()
