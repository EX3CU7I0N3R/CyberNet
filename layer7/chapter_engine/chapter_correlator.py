from __future__ import annotations


class ChapterCorrelator:
    MAX_CHAPTERS = 20

    def correlate(self, chapters):
        ordered = sorted(chapters, key=lambda chapter: chapter.start_time)
        merged = self._merge_same_type_neighbors(ordered)
        if len(merged) <= self.MAX_CHAPTERS:
            return merged
        return self._merge_low_importance(merged)

    def _merge_same_type_neighbors(self, chapters):
        merged = []
        for chapter in chapters:
            if merged and merged[-1].chapter_type == chapter.chapter_type:
                self._merge_into(merged[-1], chapter)
            else:
                merged.append(chapter)
        return merged

    def _merge_low_importance(self, chapters):
        merged = list(chapters)
        while len(merged) > self.MAX_CHAPTERS:
            index = min(range(len(merged)), key=lambda item: merged[item].importance)
            target = max(0, index - 1)
            if index == 0 and len(merged) > 1:
                target = 1
            self._merge_into(merged[target], merged[index])
            del merged[index]
            merged.sort(key=lambda chapter: chapter.start_time)
        return merged

    def _merge_into(self, chapter, other):
        chapter.end_time = max(chapter.end_time, other.end_time)
        chapter.event_count += other.event_count
        chapter.phase_count += other.phase_count
        chapter.hosts = sorted(set(chapter.hosts) | set(other.hosts))
        chapter.key_events = list(dict.fromkeys(chapter.key_events + other.key_events))[:6]
        chapter.importance = max(chapter.importance, other.importance)
        chapter.severity = self._max_severity(chapter.severity, other.severity)
        chapter.metadata.setdefault("merged_chapter_ids", []).append(other.chapter_id)

    def _max_severity(self, left, right):
        ranks = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        return left if ranks.get(left, 0) >= ranks.get(right, 0) else right
