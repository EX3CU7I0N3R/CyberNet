import unittest

from layer7.models import TimelineEvent
from layer7.phase_engine import PhaseManager


class TestLayer7Phases(unittest.TestCase):
    def test_activity_phases_are_generated_from_event_sequence(self):
        events = [
            self._event("e1", "dns_query", "2026-05-31T00:00:00Z"),
            self._event("e2", "tls_established", "2026-05-31T00:00:01Z"),
            self._event("e3", "beaconing_started", "2026-05-31T00:00:02Z"),
            self._event("e4", "candidate_created", "2026-05-31T00:00:03Z"),
        ]

        phases = PhaseManager().build_phases(events)

        self.assertGreater(len(phases), 0)
        self.assertEqual(phases[0].phase_name, "Discovery")
        self.assertIn("Beaconing", {phase.phase_name for phase in phases})
        self.assertTrue(all(phase.events for phase in phases))

    def _event(self, event_id, event_type, timestamp):
        return TimelineEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            severity="INFO",
            host="10.2.28.88",
            description=event_type,
        )


if __name__ == "__main__":
    unittest.main()
