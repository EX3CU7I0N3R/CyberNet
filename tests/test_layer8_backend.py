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

    def _artifact_dir(self):
        temp_dir = tempfile.TemporaryDirectory()
        artifact_dir = Path(temp_dir.name)
        self._write_ndjson(artifact_dir / "replay_frames.ndjson", self._frames())
        self._write_ndjson(artifact_dir / "timeline_events.ndjson", self._events())
        self._write_ndjson(artifact_dir / "activity_phases.ndjson", self._phases())
        self._write_ndjson(artifact_dir / "major_chapters.ndjson", self._chapters())
        self._write_ndjson(artifact_dir / "host_timelines.ndjson", self._host_timelines())
        self._write_ndjson(artifact_dir / "investigation_narratives.ndjson", self._narratives())
        return temp_dir

    def _write_ndjson(self, path, rows):
        with path.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row) + "\n")

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


if __name__ == "__main__":
    unittest.main()
