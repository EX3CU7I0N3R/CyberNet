from datetime import datetime, timezone
from statistics import mean
from typing import Dict, Iterable

from ingestion.parse import IPClassification


LONG_LIVED_FLOW_SECONDS = 300
PERSISTENT_FLOW_SECONDS = 900


def compute_host_metrics(host_ip: str, state: Dict) -> Dict:
    flows = state["flows"]
    flow_count = len(flows)
    packet_count = sum(_flow_packets(flow, host_ip) for flow in flows)
    upload_bytes = sum(_upload_bytes(flow, host_ip) for flow in flows)
    download_bytes = sum(_download_bytes(flow, host_ip) for flow in flows)
    total_bytes = upload_bytes + download_bytes
    durations = [max(getattr(flow, "raw_duration_seconds", 0.0), 0.0) for flow in flows]
    active_duration = _active_duration(state)
    active_bucket_count = len(state["time_buckets"])

    outbound_count = state["directions"].get("outbound", 0)
    inbound_count = state["directions"].get("inbound", 0)
    internal_count = state["directions"].get("internal", 0)
    external_count = (
        outbound_count
        + inbound_count
        + state["directions"].get("external", 0)
    )

    beacon_count = sum(1 for flow in flows if _is_periodic(flow))
    suspicious_count = sum(1 for flow in flows if getattr(flow, "is_suspicious", False))
    suppressed_count = sum(1 for flow in flows if getattr(flow, "suppressed", False))
    persistent_count = sum(1 for flow in flows if getattr(flow, "raw_duration_seconds", 0.0) >= PERSISTENT_FLOW_SECONDS)
    long_lived_count = sum(1 for flow in flows if getattr(flow, "raw_duration_seconds", 0.0) >= LONG_LIVED_FLOW_SECONDS)
    external_peers = {peer for peer in state["peers"] if IPClassification.classify(peer) == "external"}
    internal_peers = {peer for peer in state["peers"] if IPClassification.classify(peer) == "internal"}
    persistent_peers = {
        peer for peer, peer_flows in state["peer_flows"].items()
        if any(getattr(flow, "raw_duration_seconds", 0.0) >= PERSISTENT_FLOW_SECONDS for flow in peer_flows)
    }
    protocol_relationships = {
        (peer, flow.application_protocol)
        for peer, peer_flows in state["peer_flows"].items()
        for flow in peer_flows
        if flow.application_protocol
    }
    unknown_protocol_ratio = _ratio(
        sum(1 for flow in flows if flow.application_protocol == "unknown"),
        flow_count,
    )
    encrypted_flow_ratio = _ratio(
        sum(1 for flow in flows if flow.application_protocol in {"https", "http2", "smtps", "ldaps", "imaps", "pops"}),
        flow_count,
    )
    protocol_confidence_avg = round(mean([flow.app_confidence for flow in flows]), 4) if flows else 0.0
    telemetry_completeness = _telemetry_completeness(
        flow_count=flow_count,
        unknown_protocol_ratio=unknown_protocol_ratio,
        protocol_confidence_avg=protocol_confidence_avg,
        packet_count=packet_count,
        active_duration=active_duration,
    )
    activity_cluster_count = _activity_cluster_count(state["time_buckets"])

    return {
        "flow_count": flow_count,
        "external_flow_count": external_count,
        "internal_flow_count": internal_count,
        "initiated_flow_count": state["roles"].get("initiator", 0),
        "responded_flow_count": state["roles"].get("responder", 0),
        "packet_count": packet_count,
        "total_bytes": total_bytes,
        "upload_bytes": upload_bytes,
        "download_bytes": download_bytes,
        "upload_download_ratio": _ratio(upload_bytes, download_bytes),
        "average_flow_duration": round(mean(durations), 4) if durations else 0.0,
        "external_connections": external_count,
        "external_unique_hosts": len(external_peers),
        "external_unique_relationships": len(external_peers),
        "internal_connections": internal_count,
        "internal_unique_hosts": len(internal_peers),
        "internal_unique_relationships": len(internal_peers),
        "inbound_connections": inbound_count,
        "outbound_connections": outbound_count,
        "unique_destinations": len(state["destinations"]),
        "unique_peers": len(state["peers"]),
        "unique_ports": len(state["ports"]),
        "protocol_relationships": len(protocol_relationships),
        "persistent_relationships": len(persistent_peers),
        "protocols": sorted(protocol for protocol in state["protocols"] if protocol),
        "transports": sorted(transport for transport in state["transports"] if transport),
        "protocol_diversity": len(state["protocols"]),
        "transport_diversity": len(state["transports"]),
        "unknown_protocol_ratio": unknown_protocol_ratio,
        "encrypted_flow_ratio": encrypted_flow_ratio,
        "protocol_confidence_avg": protocol_confidence_avg,
        "telemetry_completeness": telemetry_completeness,
        "outbound_ratio": _ratio(outbound_count, flow_count),
        "inbound_ratio": _ratio(inbound_count, flow_count),
        "internal_ratio": _ratio(internal_count, flow_count),
        "beacon_flow_count": beacon_count,
        "suspicious_flow_count": suspicious_count,
        "suppressed_flow_count": suppressed_count,
        "persistent_connection_count": persistent_count,
        "long_lived_flow_count": long_lived_count,
        "periodic_flow_ratio": _ratio(beacon_count, flow_count),
        "persistent_connection_ratio": _ratio(persistent_count, flow_count),
        "first_seen": _format_timestamp(state["first_seen"]),
        "last_seen": _format_timestamp(state["last_seen"]),
        "first_seen_sequence": state["first_seen_sequence"],
        "last_seen_sequence": state["last_seen_sequence"],
        "first_timeline_index": state["first_timeline_index"],
        "last_timeline_index": state["last_timeline_index"],
        "active_duration": active_duration,
        "activity_density": round(flow_count / max(active_bucket_count, 1), 4),
        "session_density": _ratio(flow_count, max(active_duration / 3600, 1)),
        "activity_cluster_count": activity_cluster_count,
        "active_time_buckets": sorted(state["time_buckets"]),
        "hourly_activity_distribution": dict(sorted(state["hourly_activity"].items())),
        "graph_weight": round(total_bytes / 1_000_000 + flow_count, 4),
        "graph_degree": len(state["peers"]),
        "graph_importance": _graph_importance(flow_count, len(state["peers"]), external_count),
        "edge_hints": _edge_hints(host_ip, state["peer_flows"]),
    }


def _flow_packets(flow, host_ip: str) -> int:
    if flow.initiator_ip == host_ip:
        return flow.initiator_packets
    if flow.responder_ip == host_ip:
        return flow.responder_packets
    return flow.packet_count


def _upload_bytes(flow, host_ip: str) -> int:
    if flow.initiator_ip == host_ip:
        return flow.initiator_bytes
    if flow.responder_ip == host_ip:
        return flow.responder_bytes
    return 0


def _download_bytes(flow, host_ip: str) -> int:
    if flow.initiator_ip == host_ip:
        return flow.responder_bytes
    if flow.responder_ip == host_ip:
        return flow.initiator_bytes
    return 0


def _is_periodic(flow) -> bool:
    return getattr(flow, "beacon_score", None) is not None and flow.beacon_score >= 0.65


def _ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 4)


def _active_duration(state: Dict) -> float:
    if state["first_seen"] is None or state["last_seen"] is None:
        return 0.0
    return round((state["last_seen"] - state["first_seen"]).total_seconds(), 4)


def _graph_importance(flow_count: int, graph_degree: int, external_count: int) -> float:
    importance = min(flow_count / 250, 1.0) * 0.35
    importance += min(graph_degree / 50, 1.0) * 0.35
    importance += min(external_count / 50, 1.0) * 0.30
    return round(importance, 4)


def _telemetry_completeness(
    flow_count: int,
    unknown_protocol_ratio: float,
    protocol_confidence_avg: float,
    packet_count: int,
    active_duration: float,
) -> float:
    flow_quality = min(flow_count / 50, 1.0)
    packet_quality = min(packet_count / 750, 1.0)
    duration_quality = min(active_duration / 3600, 1.0)
    protocol_quality = max(protocol_confidence_avg, 0.0) * (1 - min(unknown_protocol_ratio, 0.85))
    return round(flow_quality * 0.25 + packet_quality * 0.25 + duration_quality * 0.20 + protocol_quality * 0.30, 4)


def _activity_cluster_count(time_buckets: set[str]) -> int:
    if not time_buckets:
        return 0

    ordered_hours = sorted(_parse_bucket(bucket) for bucket in time_buckets)
    clusters = 1
    previous_hour = ordered_hours[0]
    for hour in ordered_hours[1:]:
        if (hour - previous_hour).total_seconds() > 3600:
            clusters += 1
        previous_hour = hour
    return clusters


def _edge_hints(host_ip: str, peer_flows: Dict[str, Iterable]) -> list[Dict]:
    edges = []
    for peer_ip, flows in sorted(peer_flows.items()):
        flow_list = list(flows)
        protocols = sorted({flow.application_protocol for flow in flow_list if flow.application_protocol})
        edges.append({
            "source": host_ip,
            "target": peer_ip,
            "flow_count": len(flow_list),
            "protocols": protocols,
            "total_bytes": sum(flow.initiator_bytes + flow.responder_bytes for flow in flow_list),
            "first_seen": min(flow.timestamp_first for flow in flow_list),
            "last_seen": max(flow.timestamp_last for flow in flow_list),
        })
    return edges


def _format_timestamp(timestamp: datetime | None) -> str | None:
    if timestamp is None:
        return None
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_bucket(bucket: str) -> datetime:
    parsed_bucket = datetime.fromisoformat(bucket.replace("Z", "+00:00"))
    if parsed_bucket.tzinfo is None:
        parsed_bucket = parsed_bucket.replace(tzinfo=timezone.utc)
    return parsed_bucket.astimezone(timezone.utc)
