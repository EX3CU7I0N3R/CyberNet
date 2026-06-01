from __future__ import annotations

import json
import csv
from bisect import bisect_left
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from layer8_backend.schemas import (
    ActivityPhaseDTO,
    ChapterDTO,
    HostDTO,
    ArtifactHealthDTO,
    CandidateContextDTO,
    NarrativeDTO,
    CommunityContextDTO,
    ContextSummaryDTO,
    DestinationContextDTO,
    HypothesisContextDTO,
    RankedHostDTO,
    ReplayFrameDTO,
    RelationshipContextDTO,
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
        self.hypotheses: List[HypothesisContextDTO] = []
        self.candidates: List[CandidateContextDTO] = []
        self.relationships: List[RelationshipContextDTO] = []
        self.ranked_hosts: List[RankedHostDTO] = []
        self.destinations: List[DestinationContextDTO] = []
        self.community = CommunityContextDTO()
        self.health = ArtifactHealthDTO()
        self._frame_by_key: Dict[str, ReplayFrameDTO] = {}
        self._frame_timestamps: List[datetime] = []

    def load(self) -> None:
        if self._loaded:
            return

        raw_frames = list(self._read_ndjson("replay_frames.ndjson", required=False))
        raw_events = list(self._read_ndjson("timeline_events.ndjson", required=False))
        raw_phases = list(self._read_ndjson("activity_phases.ndjson", required=False))
        raw_chapters = list(self._read_ndjson("major_chapters.ndjson", required=False))
        raw_host_timelines = list(self._read_ndjson("host_timelines.ndjson", required=False))
        raw_narratives = list(self._read_ndjson("investigation_narratives.ndjson", required=False))
        raw_hypotheses = list(self._read_ndjson("layer5_hypotheses.ndjson", required=False))
        raw_candidates = list(self._read_ndjson("layer5_investigation_candidates.ndjson", required=False))
        raw_relationships = list(self._read_ndjson("relationships.ndjson", required=False))
        raw_host_profiles = list(self._read_ndjson("host_profiles.ndjson", required=False))
        raw_enriched_flows = list(self._read_ndjson("enriched_flows.ndjson", required=False))

        self.events = [self._event_dto(event) for event in raw_events]
        self.phases = [self._phase_dto(phase) for phase in raw_phases]
        self.chapters = [self._chapter_dto(index, chapter) for index, chapter in enumerate(raw_chapters, 1)]
        self.frames = [self._frame_dto(index, frame) for index, frame in enumerate(raw_frames, 1)]
        self.narratives = [self._narrative_dto(narrative) for narrative in raw_narratives]
        self.hosts = self._host_dtos(raw_host_timelines, raw_host_profiles)
        self.hypotheses = [self._hypothesis_dto(hypothesis) for hypothesis in raw_hypotheses]
        self.candidates = [self._candidate_dto(candidate) for candidate in raw_candidates]
        self.relationships = self._relationship_dtos(raw_relationships)
        if not self.hypotheses and not self.candidates:
            self.hypotheses, self.candidates = self._context_findings(raw_enriched_flows, raw_host_profiles)
        self.community = self._community_dto()
        self.health = self._health_dto()
        self.ranked_hosts = self._ranked_host_dtos(raw_host_profiles)
        self.destinations = self._destination_dtos()
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

    def summary(self) -> ContextSummaryDTO:
        self.load()
        primary = self.hypotheses[0].metadata if self.hypotheses else {}
        return ContextSummaryDTO(
            frame_count=len(self.frames),
            duration=self.duration_seconds(),
            event_count=len(self.events),
            chapter_count=len(self.chapters),
            node_count=self.community.graph_nodes or len(self.hosts),
            community_count=len(self.community.community_distribution),
            hypothesis_count=len(self.hypotheses),
            candidate_count=len(self.candidates),
            top_host=self.candidates[0].host if self.candidates else (self.narratives[0].host if self.narratives else None),
            primary_destination=primary.get("relationship_destination"),
            snapshot_quality=self.health.snapshot_quality.get("quality_score"),
            validations={
                "graph": self.health.graph_consistency.get("valid"),
                "hypotheses": self.health.hypothesis_validation.get("valid"),
                "candidates": self.health.candidate_validation.get("valid"),
                "snapshots": self.health.snapshot_quality.get("valid"),
                "layer6_ready": self.health.layer6_readiness.get("ready"),
            },
        )

    def relationships_for(self, host: str | None = None) -> List[RelationshipContextDTO]:
        self.load()
        if not host:
            return self.relationships
        return [
            relationship for relationship in self.relationships
            if relationship.source == host or relationship.target == host
        ]

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

    def _read_json(self, filename: str) -> Dict[str, Any]:
        path = self.artifact_dir / filename
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _read_csv(self, filename: str) -> List[Dict[str, Any]]:
        path = self.artifact_dir / filename
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

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

    def _host_dtos(
        self,
        host_timelines: List[Dict[str, Any]],
        host_profiles: List[Dict[str, Any]],
    ) -> Dict[str, HostDTO]:
        events_by_id = {event.id: event for event in self.events}
        latest_nodes = self._latest_nodes_by_ip()
        profile_by_host = {profile.get("ip_address", ""): profile for profile in host_profiles}
        hosts = {}
        for timeline in host_timelines:
            ip = timeline.get("host", "")
            node = latest_nodes.get(ip, {})
            profile = profile_by_host.get(ip, {})
            timeline_events = [
                events_by_id[event["event_id"]]
                for event in timeline.get("events", [])
                if event.get("event_id") in events_by_id
            ]
            chapters = timeline.get("chapters", [])
            hosts[ip] = HostDTO(
                ip=ip,
                risk=profile.get("risk_score", node.get("risk_score", 0.0)),
                role=profile.get("role", node.get("role", "UNKNOWN")),
                mac_address=profile.get("mac_address") or node.get("mac_address"),
                hostname=profile.get("hostname") or node.get("hostname"),
                user_identity=profile.get("user_identity") or node.get("user_identity"),
                user_full_name=profile.get("user_full_name") or node.get("user_full_name"),
                storyline=chapters,
                events=timeline_events,
                chapters=chapters,
            )
        return hosts

    def _hypothesis_dto(self, hypothesis: Dict[str, Any]) -> HypothesisContextDTO:
        return HypothesisContextDTO(
            hypothesis_id=hypothesis.get("hypothesis_id", ""),
            hypothesis_type=hypothesis.get("hypothesis_type", ""),
            title=hypothesis.get("title", ""),
            summary=hypothesis.get("summary", ""),
            impacted_entities=hypothesis.get("impacted_entities", []),
            supporting_evidence=hypothesis.get("supporting_evidence", []),
            contradictory_evidence=hypothesis.get("contradictory_evidence", []),
            confidence_explanation=hypothesis.get("confidence_explanation", ""),
            confidence=hypothesis.get("confidence", 0.0),
            severity=hypothesis.get("severity", ""),
            priority_score=hypothesis.get("priority_score", 0.0),
            priority_level=hypothesis.get("priority_level", ""),
            finding_tier=hypothesis.get("finding_tier", ""),
            metadata=hypothesis.get("metadata", {}),
        )

    def _candidate_dto(self, candidate: Dict[str, Any]) -> CandidateContextDTO:
        return CandidateContextDTO(
            host=candidate.get("host", ""),
            host_role=candidate.get("host_role", "UNKNOWN"),
            priority=candidate.get("priority", "LOW"),
            priority_score=candidate.get("priority_score", 0.0),
            priority_explanation=candidate.get("priority_explanation", {}),
            confidence=candidate.get("confidence", 0.0),
            risk=candidate.get("risk", 0.0),
            candidate_rationale=candidate.get("candidate_rationale", ""),
            host_summary=candidate.get("host_summary", {}),
            rationale=candidate.get("rationale", []),
            recommended_actions=candidate.get("recommended_actions", []),
            narrative_context=candidate.get("narrative_context", {}),
        )

    def _relationship_dtos(self, relationships: List[Dict[str, Any]]) -> List[RelationshipContextDTO]:
        by_pair = self._hypotheses_by_pair()
        enriched = []
        for relationship in relationships:
            source = relationship.get("source", "")
            target = relationship.get("target", "")
            hypothesis = by_pair.get((source, target)) or by_pair.get((target, source))
            metadata = hypothesis.metadata if hypothesis else {}
            enriched.append(RelationshipContextDTO(
                edge_id=relationship.get("edge_id", ""),
                source=source,
                target=target,
                risk=relationship.get("relationship_risk", 0.0),
                confidence=relationship.get("confidence", 0.0),
                severity=relationship.get("severity", ""),
                protocols=relationship.get("protocols", []),
                first_seen=relationship.get("first_seen", ""),
                last_seen=relationship.get("last_seen", ""),
                destination_rarity_score=metadata.get("destination_rarity_score"),
                destination_exclusivity_score=metadata.get("destination_exclusivity_score"),
                destination_consumer_count=metadata.get("destination_consumer_count"),
                supporting_evidence=hypothesis.supporting_evidence if hypothesis else [],
                contradictory_evidence=hypothesis.contradictory_evidence if hypothesis else [],
                confidence_explanation=hypothesis.confidence_explanation if hypothesis else "",
            ))
        return sorted(enriched, key=lambda item: item.risk, reverse=True)

    def _ranked_host_dtos(self, host_profiles: List[Dict[str, Any]]) -> List[RankedHostDTO]:
        candidate_by_host = {candidate.host: candidate for candidate in self.candidates}
        finding_counts = Counter()
        for hypothesis in self.hypotheses:
            for entity in hypothesis.impacted_entities:
                finding_counts[entity] += 1
        rows = []
        for profile in host_profiles:
            ip = profile.get("ip_address", "")
            candidate = candidate_by_host.get(ip)
            rows.append(RankedHostDTO(
                ip=ip,
                role=profile.get("role", "UNKNOWN"),
                role_confidence=profile.get("role_confidence", 0.0),
                community=profile.get("metadata", {}).get("community_type") or profile.get("graph_cluster_group", "Unknown"),
                mac_address=profile.get("mac_address"),
                hostname=profile.get("hostname"),
                user_identity=profile.get("user_identity"),
                user_full_name=profile.get("user_full_name"),
                risk=candidate.risk if candidate else profile.get("risk_score", 0.0),
                candidate_status="candidate" if candidate else "none",
                finding_count=finding_counts[ip],
                confidence=candidate.confidence if candidate else 0.0,
                priority=candidate.priority if candidate else "LOW",
                external_relationships=profile.get("external_unique_relationships", profile.get("external_relationships", 0)),
                internal_relationships=profile.get("internal_unique_relationships", profile.get("internal_relationships", 0)),
                top_protocols=profile.get("protocols", [])[:5],
            ))
        if not rows:
            for host in self.hosts.values():
                rows.append(RankedHostDTO(
                    ip=host.ip,
                    role=host.role,
                    risk=host.risk,
                    mac_address=host.mac_address,
                    hostname=host.hostname,
                    user_identity=host.user_identity,
                    user_full_name=host.user_full_name,
                ))
        return sorted(rows, key=lambda item: (item.candidate_status == "candidate", item.risk, item.confidence), reverse=True)

    def _context_findings(
        self,
        enriched_flows: List[Dict[str, Any]],
        host_profiles: List[Dict[str, Any]],
    ) -> tuple[List[HypothesisContextDTO], List[CandidateContextDTO]]:
        profile_by_host = {profile.get("ip_address", ""): profile for profile in host_profiles}
        candidates = []
        for flow in enriched_flows:
            if flow.get("direction") != "outbound":
                continue
            if flow.get("application_protocol") not in {"http", "https"}:
                continue
            domains = [domain for domain in flow.get("observed_domains", []) if self._is_investigative_domain(domain)]
            if not domains:
                continue
            candidates.append((flow, domains))

        if not candidates:
            return [], []

        candidates.sort(key=lambda item: (
            item[0].get("application_protocol") == "http",
            item[1][0].endswith((".su", ".cc")),
            item[0].get("packet_count", 0),
        ), reverse=True)
        flow, domains = candidates[0]
        host = flow.get("initiator_ip", "")
        destination = flow.get("responder_ip", "")
        profile = profile_by_host.get(host, {})
        domain = domains[0]
        confidence = 78.0 if flow.get("application_protocol") == "http" else 68.0
        risk = max(float(profile.get("risk_score") or 0.0), 70.0 if flow.get("application_protocol") == "http" else 60.0)
        priority_score = round(risk * 0.35 + confidence * 0.35 + 50.0 * 0.30, 1)

        hypothesis = HypothesisContextDTO(
            hypothesis_id=f"context:{host}:{destination}:{domain}",
            hypothesis_type="external_web_activity",
            title="External Web Activity",
            summary=f"{host} communicated with {domain} at {destination}:{flow.get('responder_port')}",
            impacted_entities=[host, destination, domain],
            supporting_evidence=[
                "external_relationship",
                f"domain_observed:{domain}",
                f"protocol:{flow.get('application_protocol')}",
                "rare_destination",
            ],
            contradictory_evidence=[],
            confidence_explanation=(
                f"Confidence {confidence:.0f}%. Positive: external web relationship, observed domain {domain}, "
                "rare destination context. Negative: no Layer 5 beaconing hypothesis was generated."
            ),
            confidence=confidence,
            severity="medium",
            priority_score=priority_score,
            priority_level=self._priority_level(priority_score),
            finding_tier="PRIMARY",
            metadata={
                "relationship_consumer": host,
                "relationship_destination": destination,
                "domain": domain,
                "destination_port": flow.get("responder_port"),
                "destination_consumer_count": 1,
                "destination_rarity_score": 1.0,
                "destination_exclusivity_score": 1.0,
                "source": "context_fallback",
            },
        )
        candidate = CandidateContextDTO(
            host=host,
            host_role=profile.get("role", "UNKNOWN"),
            priority=self._priority_level(priority_score),
            priority_score=priority_score,
            priority_explanation={
                "priority_score": priority_score,
                "host_risk": risk,
                "confidence": confidence,
                "criticality": 50.0,
            },
            confidence=confidence,
            risk=risk,
            candidate_rationale=f"Host has externally visible web activity to rare domain {domain} at {destination}.",
            host_summary={
                "host_role": profile.get("role", "UNKNOWN"),
                "hostname": profile.get("hostname"),
                "mac_address": profile.get("mac_address"),
                "user_identity": profile.get("user_identity"),
                "external_relationships": profile.get("external_unique_relationships", 0),
                "internal_relationships": profile.get("internal_unique_relationships", 0),
                "top_protocols": profile.get("protocols", [])[:5],
            },
            rationale=["external_web_activity", f"domain:{domain}", f"destination:{destination}"],
            recommended_actions=[
                "inspect endpoint",
                "review browser and process telemetry",
                "investigate destination domain",
                "preserve host identity evidence",
            ],
            narrative_context={"findings": [hypothesis.model_dump()]},
        )
        return [hypothesis], [candidate]

    @staticmethod
    def _is_investigative_domain(domain: str) -> bool:
        normalized = domain.lower().strip(".")
        if not normalized or "." not in normalized:
            return False
        benign_fragments = (
            "microsoft", "windows", "office", "msn.com", "bing.com", "google",
            "gstatic", "googleapis", "cloudflare", "akamai", "azureedge",
            "adobe", "mozilla", "digicert", "msft", "live.com",
        )
        return not any(fragment in normalized for fragment in benign_fragments)

    @staticmethod
    def _priority_level(score: float) -> str:
        if score >= 85:
            return "CRITICAL"
        if score >= 70:
            return "HIGH"
        if score >= 45:
            return "MEDIUM"
        return "LOW"

    def _destination_dtos(self) -> List[DestinationContextDTO]:
        destination_risk: Dict[str, float] = {}
        consumers: Dict[str, set[str]] = {}
        for relationship in self.relationships:
            destination_risk[relationship.target] = max(destination_risk.get(relationship.target, 0.0), relationship.risk)
            consumers.setdefault(relationship.target, set()).add(relationship.source)
        hypotheses_by_destination: Dict[str, List[HypothesisContextDTO]] = {}
        for hypothesis in self.hypotheses:
            destination = hypothesis.metadata.get("relationship_destination")
            if destination:
                hypotheses_by_destination.setdefault(destination, []).append(hypothesis)
        destinations = []
        for destination, hypotheses in hypotheses_by_destination.items():
            primary = hypotheses[0]
            metadata = primary.metadata
            destinations.append(DestinationContextDTO(
                ip=destination,
                related_host=metadata.get("relationship_consumer", ""),
                risk=destination_risk.get(destination, 0.0),
                consumer_count=metadata.get("destination_consumer_count", len(consumers.get(destination, set()))),
                rarity_score=metadata.get("destination_rarity_score"),
                exclusivity_score=metadata.get("destination_exclusivity_score"),
                contradictory_evidence=sorted({item for hypothesis in hypotheses for item in hypothesis.contradictory_evidence}),
                supporting_evidence=sorted({item for hypothesis in hypotheses for item in hypothesis.supporting_evidence}),
                hypothesis_count=len(hypotheses),
            ))
        return sorted(destinations, key=lambda item: ((item.exclusivity_score or 0), (item.rarity_score or 0), item.risk), reverse=True)

    def _community_dto(self) -> CommunityContextDTO:
        consistency = self._read_json("graph_consistency.json")
        rows = self._read_csv("community_audit.csv")
        nodes = [
            {
                "ip": row.get("ip", ""),
                "role": row.get("role", "UNKNOWN"),
                "role_confidence": float(row.get("role_confidence") or 0.0),
                "community": row.get("community", "Unknown"),
                "is_internal": row.get("is_internal") == "True",
                "is_external": row.get("is_external") == "True",
                "risk_score": float(row.get("risk_score") or 0.0),
            }
            for row in rows
        ]
        return CommunityContextDTO(
            graph_nodes=consistency.get("graph_nodes", len(nodes)),
            classified_nodes=consistency.get("classified_nodes", len(nodes)),
            unclassified_nodes=consistency.get("unclassified_nodes", 0),
            community_distribution=consistency.get("community_distribution", dict(Counter(node["community"] for node in nodes))),
            role_count=consistency.get("role_count", dict(Counter(node["role"] for node in nodes))),
            nodes=nodes,
            valid=consistency.get("valid", bool(nodes)),
        )

    def _health_dto(self) -> ArtifactHealthDTO:
        return ArtifactHealthDTO(
            graph_consistency=self._read_json("graph_consistency.json"),
            hypothesis_validation=self._read_json("hypothesis_validation.json"),
            candidate_validation=self._read_json("investigation_candidate_validation.json"),
            snapshot_quality=self._read_json("snapshot_quality.json"),
            role_consistency=self._read_json("role_consistency_report.json"),
            layer6_readiness=self._read_json("layer6_readiness.json"),
        )

    def _hypotheses_by_pair(self) -> Dict[tuple[str, str], HypothesisContextDTO]:
        pairs = {}
        for hypothesis in self.hypotheses:
            source = hypothesis.metadata.get("relationship_consumer")
            destination = hypothesis.metadata.get("relationship_destination")
            if source and destination:
                pairs[(source, destination)] = hypothesis
        return pairs

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
