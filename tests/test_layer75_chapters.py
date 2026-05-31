import json
import tempfile
import unittest

from layer7 import TimelineManager, export_chapter_index, export_major_chapters
from layer7.chapter_engine import ChapterManager
from layer7.models import ActivityPhase, TimelineEvent


class TestLayer75Chapters(unittest.TestCase):
    def test_chapter_generation_and_merging(self):
        chapters = ChapterManager().build_chapters(
            self._events(),
            self._phases(),
            investigation_candidates=[],
        )

        self.assertGreaterEqual(len(chapters), 5)
        self.assertLessEqual(len(chapters), 20)
        self.assertEqual([chapter.start_time for chapter in chapters], sorted(chapter.start_time for chapter in chapters))
        self.assertEqual(chapters[0].title, "Initial Network Activity")
        self.assertIn("Beaconing Indicators", [chapter.title for chapter in chapters])
        self.assertGreater(
            self._chapter(chapters, "Investigation Priority").importance,
            self._chapter(chapters, "Initial Network Activity").importance,
        )

    def test_chapter_export_generation(self):
        chapters = ChapterManager().build_chapters(self._events(), self._phases(), investigation_candidates=[])

        with tempfile.TemporaryDirectory() as tmpdir:
            chapters_path = f"{tmpdir}/major_chapters.ndjson"
            index_path = f"{tmpdir}/chapter_index.json"
            export_major_chapters(chapters, chapters_path)
            export_chapter_index(chapters, index_path)

            with open(chapters_path, encoding="utf-8") as stream:
                exported_chapters = [json.loads(line) for line in stream]
            with open(index_path, encoding="utf-8") as stream:
                chapter_index = json.load(stream)

        self.assertEqual(len(exported_chapters), len(chapters))
        self.assertEqual(chapter_index["chapter_count"], len(chapters))
        self.assertEqual(chapter_index["chapters"][0]["title"], chapters[0].title)

    def test_host_timelines_include_chapters(self):
        manager = TimelineManager()
        chapters = ChapterManager().build_chapters(self._events(), self._phases(), investigation_candidates=[])

        host_timelines = manager._host_timelines(self._events(), chapters)
        timeline = {host_timeline.host: host_timeline for host_timeline in host_timelines}["10.2.28.88"]

        self.assertTrue(timeline.chapters)
        self.assertIn("Beaconing Indicators", [chapter["title"] for chapter in timeline.chapters])

    def _events(self):
        return [
            self._event("e1", "host_role_assigned", "2026-05-31T00:00:00Z", "INFO"),
            self._event("e2", "dns_query", "2026-05-31T00:00:10Z", "INFO"),
            self._event("e3", "relationship_created", "2026-05-31T00:01:00Z", "LOW"),
            self._event("e4", "tls_established", "2026-05-31T00:02:00Z", "MEDIUM"),
            self._event("e5", "relationship_persistent", "2026-05-31T00:10:00Z", "MEDIUM"),
            self._event("e6", "beaconing_started", "2026-05-31T00:20:00Z", "HIGH"),
            self._event("e7", "candidate_created", "2026-05-31T00:30:00Z", "HIGH"),
        ]

    def _phases(self):
        return [
            ActivityPhase(
                phase_id="p1",
                phase_name="Discovery",
                start_time="2026-05-31T00:00:00Z",
                end_time="2026-05-31T00:01:00Z",
                events=["e1", "e2", "e3"],
            ),
            ActivityPhase(
                phase_id="p2",
                phase_name="Beaconing",
                start_time="2026-05-31T00:10:00Z",
                end_time="2026-05-31T00:30:00Z",
                events=["e5", "e6", "e7"],
            ),
        ]

    def _event(self, event_id, event_type, timestamp, severity):
        return TimelineEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            severity=severity,
            host="10.2.28.88",
            related_hosts=["45.131.214.85"],
            description=event_type,
            metadata={"hypothesis_type": "beaconing"} if event_type == "hypothesis_created" else {},
        )

    def _chapter(self, chapters, title):
        return next(chapter for chapter in chapters if chapter.title == title)


if __name__ == "__main__":
    unittest.main()
