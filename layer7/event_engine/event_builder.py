from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterable, List

from layer7.models import TimelineEvent

from .event_classifier import EventClassifier


class EventBuilder:
    MAX_NETWORK_EVENTS = 300
    MAX_RELATIONSHIP_EVENTS = 300

    def __init__(self):
        self.classifier = EventClassifier()
        self._candidate_timestamps = {}
        self._relationship_timestamps = {}

    def build(
        self,
        enriched_flows: Iterable,
        host_profiles: Iterable,
        relationships: Iterable,
        graph_state,
        hypotheses: Iterable,
        investigation_candidates: Iterable,
        investigation_narratives: Iterable,
    ) -> List[TimelineEvent]:
        events: List[TimelineEvent] = []
        self._relationship_timestamps = self._relationship_timestamp_lookup(relationships)
        events.extend(self._network_events(enriched_flows))
        events.extend(self._host_events(host_profiles, graph_state))
        events.extend(self._relationship_events(relationships))
        events.extend(self._hypothesis_events(hypotheses))
        events.extend(self._candidate_events(investigation_candidates))
        self._candidate_timestamps = {
            getattr(candidate, "host", ""): self._candidate_timestamp(candidate)
            for candidate in investigation_candidates
        }
        events.extend(self._narrative_events(investigation_narratives))
        return events

    def _network_events(self, enriched_flows: Iterable) -> List[TimelineEvent]:
        scored_flows = sorted(
            enriched_flows,
            key=lambda flow: (
                getattr(flow, "behavioral_score", 0.0),
                getattr(flow, "packet_count", 0),
            ),
            reverse=True,
        )[: self.MAX_NETWORK_EVENTS]

        events = []
        for flow in scored_flows:
            event_type = self.classifier.flow_event_type(flow)
            destination = getattr(flow, "responder_ip", "")
            protocol = getattr(flow, "application_protocol", "unknown")
            events.append(self._event(
                timestamp=getattr(flow, "timestamp_first", ""),
                event_type=event_type,
                severity=self.classifier.severity_for_score(getattr(flow, "behavioral_score", 0.0)),
                host=getattr(flow, "initiator_ip", ""),
                related_hosts=[destination] if destination else [],
                description=f"{protocol.upper()} relationship observed between {flow.initiator_ip} and {destination}",
                metadata={
                    "flow_id": getattr(flow, "flow_id", ""),
                    "protocol": protocol,
                    "packet_count": getattr(flow, "packet_count", 0),
                    "bytes": getattr(flow, "initiator_bytes", 0) + getattr(flow, "responder_bytes", 0),
                    "behavioral_score": getattr(flow, "behavioral_score", 0.0),
                },
            ))
        return events

    def _host_events(self, host_profiles: Iterable, graph_state) -> List[TimelineEvent]:
        profiles_by_ip = {profile.ip_address: profile for profile in host_profiles}
        nodes = getattr(graph_state, "nodes", [])
        events = []
        for node in nodes:
            profile = profiles_by_ip.get(node.ip_address)
            timestamp = node.first_seen or getattr(profile, "first_seen", None) or getattr(graph_state, "timestamp", "")
            role = getattr(node, "role", "UNKNOWN")
            community = node.metadata.get("community", "UNKNOWN") if getattr(node, "metadata", None) else "UNKNOWN"
            events.append(self._event(
                timestamp=timestamp,
                event_type="host_role_assigned",
                severity=self.classifier.severity_for_score(getattr(node, "risk_score", 0.0)),
                host=node.ip_address,
                description=f"{node.ip_address} classified as {role}",
                metadata={"role": role, "risk_score": getattr(node, "risk_score", 0.0)},
            ))
            events.append(self._event(
                timestamp=timestamp,
                event_type="community_assigned",
                severity="INFO",
                host=node.ip_address,
                description=f"{node.ip_address} assigned to {community}",
                metadata={"community": community},
            ))
        return events

    def _relationship_events(self, relationships: Iterable) -> List[TimelineEvent]:
        ranked_relationships = sorted(
            relationships,
            key=lambda rel: (
                getattr(rel, "relationship_risk", 0.0),
                getattr(rel, "packet_count", 0),
                getattr(rel, "total_bytes", 0),
            ),
            reverse=True,
        )[: self.MAX_RELATIONSHIP_EVENTS]

        events = []
        for relationship in ranked_relationships:
            source = getattr(relationship, "source", "")
            target = getattr(relationship, "target", "")
            relationship_type = "relationship_persistent" if getattr(relationship, "persistence", 0.0) >= 0.5 else "relationship_created"
            events.append(self._event(
                timestamp=getattr(relationship, "first_seen", ""),
                event_type=relationship_type,
                severity=self.classifier.severity_for_score(getattr(relationship, "relationship_risk", 0.0)),
                host=source,
                related_hosts=[target] if target else [],
                description=f"Relationship observed between {source} and {target}",
                metadata={
                    "edge_id": getattr(relationship, "edge_id", ""),
                    "risk": getattr(relationship, "relationship_risk", 0.0),
                    "persistence": getattr(relationship, "persistence", 0.0),
                    "protocols": getattr(relationship, "protocols", []),
                },
            ))
        return events

    def _hypothesis_events(self, hypotheses: Iterable) -> List[TimelineEvent]:
        events = []
        for hypothesis in hypotheses:
            host = self._primary_host(getattr(hypothesis, "impacted_entities", []))
            timestamp = self._hypothesis_timestamp(hypothesis)
            events.append(self._event(
                timestamp=timestamp,
                event_type="hypothesis_created",
                severity=self.classifier.severity_for_label(getattr(hypothesis, "severity", "")),
                host=host,
                related_hosts=[entity for entity in getattr(hypothesis, "impacted_entities", []) if entity != host],
                description=getattr(hypothesis, "summary", getattr(hypothesis, "title", "")),
                metadata={
                    "hypothesis_id": getattr(hypothesis, "hypothesis_id", ""),
                    "hypothesis_type": getattr(hypothesis, "hypothesis_type", ""),
                    "confidence": getattr(hypothesis, "confidence", 0.0),
                    "priority_score": getattr(hypothesis, "priority_score", 0.0),
                },
            ))
            if getattr(hypothesis, "hypothesis_type", "") == "beaconing":
                events.append(self._event(
                    timestamp=timestamp,
                    event_type="beaconing_started",
                    severity=self.classifier.severity_for_score(getattr(hypothesis, "confidence", 0.0)),
                    host=host,
                    related_hosts=[entity for entity in getattr(hypothesis, "impacted_entities", []) if entity != host],
                    description=getattr(hypothesis, "confidence_explanation", "") or getattr(hypothesis, "summary", ""),
                    metadata={"hypothesis_id": getattr(hypothesis, "hypothesis_id", "")},
                ))
        return events

    def _candidate_events(self, investigation_candidates: Iterable) -> List[TimelineEvent]:
        events = []
        for candidate in investigation_candidates:
            events.append(self._event(
                timestamp=self._candidate_timestamp(candidate),
                event_type="candidate_created",
                severity=self.classifier.severity_for_label(getattr(candidate, "priority", "")),
                host=getattr(candidate, "host", ""),
                description=getattr(candidate, "candidate_rationale", "") or f"Investigation candidate created for {candidate.host}",
                metadata={
                    "priority": getattr(candidate, "priority", ""),
                    "priority_score": getattr(candidate, "priority_score", 0.0),
                    "confidence": getattr(candidate, "confidence", 0.0),
                    "risk": getattr(candidate, "risk", 0.0),
                },
            ))
        return events

    def _narrative_events(self, investigation_narratives: Iterable) -> List[TimelineEvent]:
        events = []
        for narrative in investigation_narratives:
            timestamp = self._candidate_timestamps.get(getattr(narrative, "host", ""), "")
            hypotheses = getattr(narrative, "supporting_hypotheses", [])
            if hypotheses and isinstance(hypotheses[0], dict):
                timestamp = hypotheses[0].get("created_at", "")
            events.append(self._event(
                timestamp=timestamp,
                event_type="narrative_generated",
                severity=self.classifier.severity_for_label(getattr(narrative, "priority", "")),
                host=getattr(narrative, "host", ""),
                description=getattr(narrative, "executive_summary", ""),
                metadata={
                    "priority": getattr(narrative, "priority", ""),
                    "confidence": getattr(narrative, "confidence", 0.0),
                    "quality_score": getattr(narrative, "narrative_quality_score", 0.0),
                },
            ))
        return events

    def _event(self, timestamp: str, event_type: str, severity: str, host: str, description: str, related_hosts=None, metadata=None):
        related_hosts = related_hosts or []
        metadata = metadata or {}
        event_id = self._event_id(timestamp, event_type, host, related_hosts, metadata)
        return TimelineEvent(
            timestamp=timestamp,
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            host=host,
            related_hosts=related_hosts,
            description=description,
            metadata=metadata,
        )

    def _event_id(self, timestamp: str, event_type: str, host: str, related_hosts: list[str], metadata: dict) -> str:
        key = f"{timestamp}|{event_type}|{host}|{','.join(related_hosts)}|{metadata}"
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:12]
        return f"evt_{digest}"

    def _primary_host(self, impacted_entities: list[str]) -> str:
        for entity in impacted_entities:
            if entity.startswith(("10.", "172.", "192.168.")):
                return entity
        return impacted_entities[0] if impacted_entities else ""

    def _candidate_timestamp(self, candidate) -> str:
        findings = getattr(candidate, "findings", []) or getattr(candidate, "hypotheses", [])
        if findings:
            return max((self._hypothesis_timestamp(finding) for finding in findings), key=self._parse_timestamp)
        return ""

    def _hypothesis_timestamp(self, hypothesis) -> str:
        metadata = getattr(hypothesis, "metadata", {}) or {}
        consumer = metadata.get("relationship_consumer")
        destination = metadata.get("relationship_destination")
        if consumer and destination:
            timestamp = self._relationship_timestamps.get((consumer, destination)) or self._relationship_timestamps.get((destination, consumer))
            if timestamp:
                return timestamp

        impacted_entities = getattr(hypothesis, "impacted_entities", [])
        if len(impacted_entities) >= 2:
            for source in impacted_entities:
                for target in impacted_entities:
                    if source == target:
                        continue
                    timestamp = self._relationship_timestamps.get((source, target))
                    if timestamp:
                        return timestamp

        return getattr(hypothesis, "created_at", "")

    def _relationship_timestamp_lookup(self, relationships):
        timestamps = {}
        for relationship in relationships:
            source = getattr(relationship, "source", "")
            target = getattr(relationship, "target", "")
            timestamp = getattr(relationship, "last_seen", None) or getattr(relationship, "first_seen", "")
            if source and target and timestamp:
                timestamps[(source, target)] = timestamp
        return timestamps

    def _parse_timestamp(self, timestamp: str):
        try:
            parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)
