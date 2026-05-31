from __future__ import annotations

import json
from bisect import bisect_left
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from layer8_backend.schemas import (
    ActivityPhaseDTO,
    ChapterDTO,
    HostDTO,
    NarrativeDTO,
    ReplayFrameDTO,
    TimelineEventDTO,
)


class ReplayArtifactProvider:
    def __init__(self, artifact_dir: str | Path = "output"):
        self.artifact_dir = Path(artifact_dir)
        self._loaded = False
        self.frames: List[ReplayFrameDTO] = []
        self.events: List[TimelineEventDTO] = []
        self.phases: List[ActivityPhaseDTO] = []
        self.chapters: List[ChapterDTO] = []
        self.hosts: Dict[str, HostDTO] = {}
        self.narratives: List[NarrativeDTO] = []
        self._frame_by_key: Dict[str, ReplayFrameDTO] = {}
        self._frame_timestamps: List[datetime] = []

    def load(self) -> None:
        if self._loaded:
            return

        raw_frames = list(self._read_ndjson("replay_frames.ndjson"))
        raw_events = list(self._read_ndjson("timeline_events.ndjson"))
        raw_phases = list(self._read_ndjson("activity_phases.ndjson"))
        raw_chapters = list(self._read_ndjson("major_chapters.ndjson"))
        raw_host_timelines = list(self._read_ndjson("host_timelines.ndjson"))
        raw_narratives = list(self._read_ndjson("investigation_narratives.ndjson", required=False))

        self.events = [self._event_dto(event) for event in raw_events]
        self.phases = [self._phase_dto(phase) for phase in raw_phases]
        self.chapters = [self._chapter_dto(index, chapter) for index, chapter in enumerate(raw_chapters, 1)]
        self.frames = [self._frame_dto(index, frame) for index, frame in enumerate(raw_frames, 1)]
        self.narratives = [self._narrative_dto(narrative) for narrative in raw_narratives]
        self.hosts = self._host_dtos(raw_host_timelines)
        self._frame_by_key = {frame.frame_key: frame for frame in self.frames}
        self._frame_by_key.update({str(frame.frame_id): frame for frame in self.frames})
        self._frame_timestamps = [self._parse_timestamp(frame.timestamp) for frame in self.frames]
        self._loaded = True

    def frame(self, frame_id: int | str) -> ReplayFrameDTO:
        self.load()
        key = str(frame_id)
        frame = self._frame_by_key.get(key)
        if frame is None:
            raise KeyError(f"Replay frame not found: {frame_id}")
        return frame

    def seek(self, timestamp: str) -> ReplayFrameDTO:
        self.load()
        if not self.frames:
            raise KeyError("Replay has no frames")

        target = self._parse_timestamp(timestamp)
        index = bisect_left(self._frame_timestamps, target)
        if index <= 0:
            return self.frames[0]
        if index >= len(self.frames):
            return self.frames[-1]

        before = self._frame_timestamps[index - 1]
        after = self._frame_timestamps[index]
        if abs((target - before).total_seconds()) <= abs((after - target).total_seconds()):
            return self.frames[index - 1]
        return self.frames[index]

    def duration_seconds(self) -> float:
        self.load()
        if len(self.frames) < 2:
            return 0.0
        start = self._parse_timestamp(self.frames[0].timestamp)
        end = self._parse_timestamp(self.frames[-1].timestamp)
        return round(max(0.0, (end - start).total_seconds()), 4)

    def host(self, ip: str) -> HostDTO:
        self.load()
        host = self.hosts.get(ip)
        if host is None:
            raise KeyError(f"Host not found: {ip}")
        return host

    def _read_ndjson(self, filename: str, required: bool = True) -> Iterable[Dict[str, Any]]:
        path = self.artifact_dir / filename
        if not path.exists():
            if required:
                raise FileNotFoundError(f"Layer 7 artifact not found: {path}")
            return []

        with path.open(encoding="utf-8") as stream:
            for line in stream:
                stripped = line.strip()
                if stripped:
                    yield json.loads(stripped)

    def _frame_dto(self, index: int, frame: Dict[str, Any]) -> ReplayFrameDTO:
        state = frame.get("state", {})
        return ReplayFrameDTO(
            frame_id=index,
            frame_key=frame.get("frame_id", str(index)),
            timestamp=frame.get("timestamp", ""),
            nodes=state.get("nodes", []),
            edges=state.get("edges", []),
            events=state.get("events", []),
            candidate_hosts=state.get("candidate_hosts", []),
            graph_metrics=state.get("graph_metrics", {}),
            delta=frame.get("delta", {}),
            frame_duration=frame.get("frame_duration", 0.0),
            timestamp_delta=frame.get("timestamp_delta", 0.0),
        )

    def _event_dto(self, event: Dict[str, Any]) -> TimelineEventDTO:
        return TimelineEventDTO(
            id=event.get("event_id", ""),
            timestamp=event.get("timestamp", ""),
            type=event.get("event_type", ""),
            severity=event.get("severity", "INFO"),
            host=event.get("host", ""),
            related_hosts=event.get("related_hosts", []),
            description=event.get("description", ""),
            metadata=event.get("metadata", {}),
        )

    def _phase_dto(self, phase: Dict[str, Any]) -> ActivityPhaseDTO:
        return ActivityPhaseDTO(
            id=phase.get("phase_id", ""),
            name=phase.get("phase_name", ""),
            start_time=phase.get("start_time", ""),
            end_time=phase.get("end_time", ""),
            events=phase.get("events", []),
            description=phase.get("description", ""),
        )

    def _chapter_dto(self, index: int, chapter: Dict[str, Any]) -> ChapterDTO:
        return ChapterDTO(
            id=index,
            chapter_id=chapter.get("chapter_id", str(index)),
            title=chapter.get("title", ""),
            type=chapter.get("chapter_type", "UNKNOWN"),
            description=chapter.get("description", ""),
            start_time=chapter.get("start_time", ""),
            end_time=chapter.get("end_time", ""),
            duration_seconds=chapter.get("duration_seconds", 0.0),
            event_count=chapter.get("event_count", 0),
            phase_count=chapter.get("phase_count", 0),
            hosts=chapter.get("hosts", []),
            key_events=chapter.get("key_events", []),
            severity=chapter.get("severity", "INFO"),
            importance=chapter.get("importance", 0.0),
        )

    def _narrative_dto(self, narrative: Dict[str, Any]) -> NarrativeDTO:
        return NarrativeDTO(
            host=narrative.get("host", ""),
            priority=narrative.get("priority", "LOW"),
            confidence=narrative.get("confidence", 0.0),
            executive_summary=narrative.get("executive_summary", ""),
            behavioral_summary=narrative.get("behavioral_summary", ""),
            assessment=narrative.get("assessment", ""),
            recommended_actions=narrative.get("recommended_actions", []),
            investigation_plan=narrative.get("investigation_plan", []),
            metadata={
                "risk_context": narrative.get("risk_context", {}),
                "confidence_drivers": narrative.get("confidence_drivers", {}),
                "supporting_hypotheses": narrative.get("supporting_hypotheses", []),
            },
        )

    def _host_dtos(self, host_timelines: List[Dict[str, Any]]) -> Dict[str, HostDTO]:
        events_by_id = {event.id: event for event in self.events}
        latest_nodes = self._latest_nodes_by_ip()
        hosts = {}
        for timeline in host_timelines:
            ip = timeline.get("host", "")
            node = latest_nodes.get(ip, {})
            timeline_events = [
                events_by_id[event["event_id"]]
                for event in timeline.get("events", [])
                if event.get("event_id") in events_by_id
            ]
            chapters = timeline.get("chapters", [])
            hosts[ip] = HostDTO(
                ip=ip,
                risk=node.get("risk_score", 0.0),
                role=node.get("role", "UNKNOWN"),
                storyline=chapters,
                events=timeline_events,
                chapters=chapters,
            )
        return hosts

    def _latest_nodes_by_ip(self) -> Dict[str, Dict[str, Any]]:
        if not self.frames:
            return {}
        nodes = {}
        for frame in reversed(self.frames):
            for node in frame.nodes:
                ip = node.get("ip")
                if ip and ip not in nodes:
                    nodes[ip] = node
            if nodes:
                break
        return nodes

    def _parse_timestamp(self, timestamp: str) -> datetime:
        parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
