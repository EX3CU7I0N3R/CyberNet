from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from layer7.models import MajorChapter

from .chapter_classifier import ChapterClassifier


class ChapterBuilder:
    KEY_EVENT_LIMIT = 6

    def __init__(self):
        self.classifier = ChapterClassifier()

    def build(self, timeline_events, activity_phases, investigation_candidates):
        if not timeline_events:
            return []

        buckets = self._event_buckets(timeline_events)
        chapters = []
        for chapter_type, events in buckets.items():
            if not events:
                continue
            chapters.append(self._chapter(chapter_type, events, activity_phases))

        chapters = sorted(chapters, key=lambda chapter: self._parse(chapter.start_time))
        if chapters:
            chapters[0].start_time = timeline_events[0].timestamp
            chapters[0].duration_seconds = self._duration(chapters[0].start_time, chapters[0].end_time)
            chapters[-1].end_time = timeline_events[-1].timestamp
            chapters[-1].duration_seconds = self._duration(chapters[-1].start_time, chapters[-1].end_time)

        return chapters

    def _event_buckets(self, timeline_events):
        buckets = {chapter_type: [] for chapter_type in ChapterClassifier.TITLES}
        for event in timeline_events:
            buckets[self.classifier.classify(event)].append(event)
        return {chapter_type: events for chapter_type, events in buckets.items() if events}

    def _chapter(self, chapter_type, events, activity_phases):
        start_time = min(event.timestamp for event in events)
        end_time = max(event.timestamp for event in events)
        phase_ids = self._phase_ids(start_time, end_time, activity_phases)
        chapter_id = self._chapter_id(chapter_type, start_time, end_time)
        event_types = self._key_events(events)
        hosts = sorted({event.host for event in events if event.host})
        return MajorChapter(
            chapter_id=chapter_id,
            chapter_type=chapter_type,
            title=self.classifier.title(chapter_type),
            description=self._description(chapter_type, events, event_types),
            start_time=start_time,
            end_time=end_time,
            duration_seconds=self._duration(start_time, end_time),
            event_count=len(events),
            phase_count=len(phase_ids),
            hosts=hosts,
            key_events=event_types,
            severity=self.classifier.severity(events),
            importance=self.classifier.importance(chapter_type, events),
            metadata={"phase_ids": phase_ids},
        )

    def _phase_ids(self, start_time, end_time, activity_phases):
        start = self._parse(start_time)
        end = self._parse(end_time)
        phase_ids = []
        for phase in activity_phases:
            phase_start = self._parse(phase.start_time)
            phase_end = self._parse(phase.end_time)
            if phase_start <= end and phase_end >= start:
                phase_ids.append(phase.phase_id)
        return list(dict.fromkeys(phase_ids))

    def _key_events(self, events):
        counts = {}
        severity_rank = ChapterClassifier.SEVERITY_RANK
        for event in events:
            current = counts.setdefault(event.event_type, {"count": 0, "severity": 0})
            current["count"] += 1
            current["severity"] = max(current["severity"], severity_rank.get(event.severity, 0))
        ranked = sorted(counts.items(), key=lambda item: (item[1]["severity"], item[1]["count"], item[0]), reverse=True)
        return [event_type for event_type, _ in ranked[: self.KEY_EVENT_LIMIT]]

    def _description(self, chapter_type, events, key_events):
        host_count = len({event.host for event in events if event.host})
        if chapter_type == "INITIAL_ACTIVITY":
            return f"The replay establishes the initial host and community context across {host_count} observed hosts."
        if chapter_type == "NETWORK_DISCOVERY":
            return f"Name-resolution and discovery activity provides early context for host communication paths."
        if chapter_type == "RELATIONSHIP_FORMATION":
            return f"Hosts begin forming observable network relationships that become part of the investigation timeline."
        if chapter_type == "EXTERNAL_COMMUNICATION":
            return f"External application sessions appear in the timeline, including {', '.join(key_events[:3])}."
        if chapter_type == "PERSISTENT_COMMUNICATION":
            return "One or more relationships persist across observation windows and become durable replay anchors."
        if chapter_type == "BEHAVIORAL_ESCALATION":
            return "Behavioral scoring increases as risk-relevant activity accumulates."
        if chapter_type == "BEACONING_DEVELOPMENT":
            return "Periodic and persistent communication patterns develop into a beaconing storyline."
        if chapter_type == "INVESTIGATION_TRIGGER":
            return "Layer 5 hypotheses convert timeline behavior into analyst-facing investigation findings."
        if chapter_type == "INVESTIGATION_PRIORITY":
            return "The investigation candidate and narrative milestones define the highest-priority replay jump targets."
        return "Timeline activity did not match a known chapter category."

    def _chapter_id(self, chapter_type, start_time, end_time):
        digest = hashlib.md5(f"{chapter_type}|{start_time}|{end_time}".encode("utf-8")).hexdigest()[:10]
        return f"chapter_{digest}"

    def _duration(self, start_time, end_time):
        return round(max(0.0, (self._parse(end_time) - self._parse(start_time)).total_seconds()), 4)

    def _parse(self, timestamp: str):
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
