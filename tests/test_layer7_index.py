import unittest

from layer7.models import TimelineEvent
from layer7.timeline_manager import TimelineManager


class TestLayer7Index(unittest.TestCase):
    def test_host_timelines_are_generated(self):
        events = [
            TimelineEvent(event_id="e1", timestamp="2026-05-31T00:00:00Z", event_type="dns_query", severity="INFO", host="10.2.28.88", description="dns"),
            TimelineEvent(event_id="e2", timestamp="2026-05-31T00:00:01Z", event_type="candidate_created", severity="HIGH", host="10.2.28.88", description="candidate"),
            TimelineEvent(event_id="e3", timestamp="2026-05-31T00:00:02Z", event_type="host_role_assigned", severity="INFO", host="10.2.28.2", description="role"),
        ]

        host_timelines = TimelineManager()._host_timelines(events)

        timelines_by_host = {timeline.host: timeline for timeline in host_timelines}
        self.assertIn("10.2.28.88", timelines_by_host)
        self.assertEqual(len(timelines_by_host["10.2.28.88"].events), 2)
        self.assertEqual(timelines_by_host["10.2.28.88"].events[0]["event_type"], "dns_query")


if __name__ == "__main__":
    unittest.main()
