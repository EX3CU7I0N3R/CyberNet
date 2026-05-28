from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field


class HostProfile(BaseModel):
    host: str
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    first_seen_sequence: int = 0
    last_seen_sequence: int = 0
    flow_count: int = 0
    external_connections: int = 0
    unique_destinations: int = 0
    protocols: List[str] = Field(default_factory=list)
    protocol_diversity: int = 0
    beacon_flow_count: int = 0
    suspicious_flow_count: int = 0
    suppressed_flow_count: int = 0
    upload_bytes: int = 0
    download_bytes: int = 0
    upload_download_ratio: float = 0.0
    temporal_activity: Dict[str, int] = Field(default_factory=dict)
    connection_persistence_seconds: float = 0.0
    risk_score: float = 0.0
    confidence: float = 0.0
    severity: str = "informational"
    graph_node_type: str = "host"


def build_host_profiles(enriched_flows: List) -> List[HostProfile]:
    profile_state: Dict[str, Dict] = {}

    for flow in enriched_flows:
        state = profile_state.setdefault(flow.initiator_ip, _new_state())
        state["flows"].append(flow)
        state["destinations"].add(flow.responder_ip)
        state["protocols"].add(flow.application_protocol)

        if flow.direction in {"outbound", "inbound", "external"}:
            state["external_connections"] += 1

        if flow.beacon_score is not None and flow.beacon_score >= 0.65:
            state["beacon_flow_count"] += 1

        if flow.is_suspicious:
            state["suspicious_flow_count"] += 1

        if flow.suppressed:
            state["suppressed_flow_count"] += 1

        state["upload_bytes"] += flow.initiator_bytes
        state["download_bytes"] += flow.responder_bytes
        _update_time_bounds(state, flow)

    return [_build_profile(host, state) for host, state in sorted(profile_state.items())]


def _new_state() -> Dict:
    return {
        "flows": [],
        "destinations": set(),
        "protocols": set(),
        "external_connections": 0,
        "beacon_flow_count": 0,
        "suspicious_flow_count": 0,
        "suppressed_flow_count": 0,
        "upload_bytes": 0,
        "download_bytes": 0,
        "first_seen": None,
        "last_seen": None,
        "first_seen_sequence": 0,
        "last_seen_sequence": 0,
        "temporal_activity": {},
    }


def _update_time_bounds(state: Dict, flow):
    first_seen = _parse_timestamp(flow.timestamp_first)
    last_seen = _parse_timestamp(flow.timestamp_last)

    if state["first_seen"] is None or first_seen < state["first_seen"]:
        state["first_seen"] = first_seen
        state["first_seen_sequence"] = flow.first_seen_sequence

    if state["last_seen"] is None or last_seen > state["last_seen"]:
        state["last_seen"] = last_seen
        state["last_seen_sequence"] = flow.last_seen_sequence

    bucket = first_seen.replace(minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
    state["temporal_activity"][bucket] = state["temporal_activity"].get(bucket, 0) + 1


def _build_profile(host: str, state: Dict) -> HostProfile:
    flows = state["flows"]
    risk_score = _host_risk_score(flows, state)
    confidence = _host_confidence(flows)

    upload_bytes = state["upload_bytes"]
    download_bytes = state["download_bytes"]
    upload_download_ratio = upload_bytes / download_bytes if download_bytes else float(upload_bytes > 0)

    return HostProfile(
        host=host,
        first_seen=_format_timestamp(state["first_seen"]),
        last_seen=_format_timestamp(state["last_seen"]),
        first_seen_sequence=state["first_seen_sequence"],
        last_seen_sequence=state["last_seen_sequence"],
        flow_count=len(flows),
        external_connections=state["external_connections"],
        unique_destinations=len(state["destinations"]),
        protocols=sorted(protocol for protocol in state["protocols"] if protocol),
        protocol_diversity=len(state["protocols"]),
        beacon_flow_count=state["beacon_flow_count"],
        suspicious_flow_count=state["suspicious_flow_count"],
        suppressed_flow_count=state["suppressed_flow_count"],
        upload_bytes=upload_bytes,
        download_bytes=download_bytes,
        upload_download_ratio=round(upload_download_ratio, 4),
        temporal_activity=dict(sorted(state["temporal_activity"].items())),
        connection_persistence_seconds=_connection_persistence_seconds(state),
        risk_score=risk_score,
        confidence=confidence,
        severity=_severity(risk_score, confidence),
    )


def _host_risk_score(flows: List, state: Dict) -> float:
    suspicious_pressure = min(state["suspicious_flow_count"] * 18, 45)
    beacon_pressure = min(state["beacon_flow_count"] * 12, 25)
    external_pressure = min(state["external_connections"] / 25 * 20, 20)
    destination_pressure = min(len(state["destinations"]) / 50 * 15, 15)
    protocol_pressure = min(len(state["protocols"]) / 8 * 10, 10)
    flow_pressure = min(len(flows) / 500 * 10, 10)
    return round(min(
        suspicious_pressure
        + beacon_pressure
        + external_pressure
        + destination_pressure
        + protocol_pressure
        + flow_pressure,
        100,
    ), 2)


def _host_confidence(flows: List) -> float:
    if not flows:
        return 0.0

    flow_count_quality = min(len(flows) / 50, 1.0)
    duration_quality = min(sum(max(flow.raw_duration_seconds, 0) for flow in flows) / 7200, 1.0)
    telemetry_quality = sum(flow.confidence for flow in flows) / len(flows)
    confidence = (flow_count_quality * 0.35) + (duration_quality * 0.25) + (telemetry_quality * 0.40)
    return round(min(confidence, 0.90), 4)


def _connection_persistence_seconds(state: Dict) -> float:
    if state["first_seen"] is None or state["last_seen"] is None:
        return 0.0
    return round((state["last_seen"] - state["first_seen"]).total_seconds(), 4)


def _severity(score: float, confidence: float) -> str:
    adjusted_score = score * confidence
    if adjusted_score >= 55:
        return "high"
    if adjusted_score >= 30:
        return "medium"
    if score > 0:
        return "low"
    return "informational"


def _parse_timestamp(timestamp: str) -> datetime:
    parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
    return parsed_timestamp.astimezone(timezone.utc)


def _format_timestamp(timestamp: Optional[datetime]) -> Optional[str]:
    if timestamp is None:
        return None
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
