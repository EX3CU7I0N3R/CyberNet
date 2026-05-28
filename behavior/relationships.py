from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from typing import Dict, Iterable, List

from behavior.schemas import HostRelationship


def build_relationships(enriched_flows: Iterable) -> List[HostRelationship]:
    grouped_flows: Dict[tuple[str, str], list] = defaultdict(list)
    for flow in enriched_flows:
        grouped_flows[(flow.initiator_ip, flow.responder_ip)].append(flow)

    return [
        _build_relationship(source, target, flows)
        for (source, target), flows in sorted(grouped_flows.items())
    ]


def _build_relationship(source: str, target: str, flows: list) -> HostRelationship:
    protocols = sorted({flow.application_protocol for flow in flows if flow.application_protocol})
    transports = sorted({flow.transport_layer for flow in flows if flow.transport_layer})
    timestamps_first = [_parse_timestamp(flow.timestamp_first) for flow in flows]
    timestamps_last = [_parse_timestamp(flow.timestamp_last) for flow in flows]
    first_seen = min(timestamps_first)
    last_seen = max(timestamps_last)
    active_seconds = max((last_seen - first_seen).total_seconds(), 0.0)
    temporal_buckets = sorted({
        timestamp.replace(minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
        for timestamp in timestamps_first + timestamps_last
    })
    persistence = _persistence_score(flows, active_seconds)
    risk_score, indicators = _relationship_risk(flows, protocols, persistence)
    confidence = _relationship_confidence(flows, protocols, active_seconds)

    return HostRelationship(
        edge_id=_edge_id(source, target),
        source=source,
        target=target,
        relationship_risk=risk_score,
        confidence=confidence,
        severity=_severity(risk_score, confidence),
        flows=len(flows),
        packet_count=sum(flow.packet_count for flow in flows),
        total_bytes=sum(flow.initiator_bytes + flow.responder_bytes for flow in flows),
        protocols=protocols,
        transports=transports,
        first_seen=_format_timestamp(first_seen),
        last_seen=_format_timestamp(last_seen),
        first_seen_sequence=min(flow.first_seen_sequence for flow in flows),
        last_seen_sequence=max(flow.last_seen_sequence for flow in flows),
        persistence=persistence,
        temporal_buckets=temporal_buckets,
        protocol_diversity=len(protocols),
        relationship_indicators=indicators,
        graph_weight=round(len(flows) + sum(flow.packet_count for flow in flows) / 100, 4),
        graph_edge_color=_edge_color(risk_score, confidence),
        graph_edge_width=round(min(1 + len(flows) / 12 + risk_score / 40, 8), 2),
        metadata={
            "direction": "source_to_target",
            "suspicious_flows": sum(1 for flow in flows if getattr(flow, "is_suspicious", False)),
            "suppressed_flows": sum(1 for flow in flows if getattr(flow, "suppressed", False)),
        },
    )


def _relationship_risk(flows: list, protocols: list[str], persistence: float) -> tuple[float, list[str]]:
    indicators = {}
    suspicious_count = sum(1 for flow in flows if getattr(flow, "is_suspicious", False))
    periodic_count = sum(1 for flow in flows if getattr(flow, "beacon_score", None) is not None and flow.beacon_score >= 0.65)
    suppressed_ratio = sum(1 for flow in flows if getattr(flow, "suppressed", False)) / max(len(flows), 1)

    if persistence >= 0.60:
        indicators["unusual_relationship_persistence"] = 18
    if periodic_count:
        indicators["periodic_relationship_activity"] = min(periodic_count * 12, 24)
    if suspicious_count:
        indicators["elevated_flow_context"] = min(suspicious_count * 10, 20)
    if "unknown" in protocols:
        indicators["ambiguous_protocol_relationship"] = 8
    if protocols == ["https"] and persistence >= 0.45:
        indicators["persistent_tls_relationship"] = 12

    pressure = sum(indicators.values()) * (1 - min(suppressed_ratio * 0.75, 0.75))
    risk_score = 78 * (1 - pow(2.718281828, -pressure / 42))
    return round(risk_score, 2), list(indicators)


def _relationship_confidence(flows: list, protocols: list[str], active_seconds: float) -> float:
    sample_quality = min(len(flows) / 20, 1.0)
    packet_quality = min(sum(flow.packet_count for flow in flows) / 250, 1.0)
    duration_quality = min(active_seconds / 3600, 1.0)
    protocol_quality = 0.45 if "unknown" in protocols else 0.72
    return round(min(sample_quality * 0.25 + packet_quality * 0.30 + duration_quality * 0.20 + protocol_quality * 0.25, 0.80), 4)


def _persistence_score(flows: list, active_seconds: float) -> float:
    if not flows:
        return 0.0
    duration_pressure = min(sum(max(flow.raw_duration_seconds, 0) for flow in flows) / 3600, 1.0)
    span_pressure = min(active_seconds / 7200, 1.0)
    flow_pressure = min(len(flows) / 24, 1.0)
    return round(duration_pressure * 0.45 + span_pressure * 0.35 + flow_pressure * 0.20, 4)


def _edge_id(source: str, target: str) -> str:
    return sha256(f"{source}->{target}".encode()).hexdigest()[:16]


def _severity(score: float, confidence: float) -> str:
    adjusted_score = score * confidence
    if adjusted_score >= 52:
        return "high"
    if adjusted_score >= 28:
        return "medium"
    if score > 0:
        return "low"
    return "informational"


def _edge_color(score: float, confidence: float) -> str:
    adjusted_score = score * confidence
    if adjusted_score >= 52:
        return "#d95f3d"
    if adjusted_score >= 28:
        return "#ffb347"
    if score > 0:
        return "#f0d878"
    return "#7aa6c2"


def _parse_timestamp(timestamp: str) -> datetime:
    parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
    return parsed_timestamp.astimezone(timezone.utc)


def _format_timestamp(timestamp: datetime) -> str:
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
