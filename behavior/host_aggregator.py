from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List

from behavior.baselines import normalize_host_state
from behavior.host_metrics import compute_host_metrics
from behavior.host_risk import score_host_behavior
from behavior.roles import infer_host_role
from behavior.schemas import HostGraphNode, HostProfile


def build_host_profiles(enriched_flows: Iterable) -> List[HostProfile]:
    host_states: Dict[str, Dict] = {}

    for flow in enriched_flows:
        if flow.initiator_ip == flow.responder_ip:
            _apply_self_flow(host_states, flow)
            continue

        _apply_flow_role(host_states, flow.initiator_ip, flow, "initiator", flow.responder_ip)
        _apply_flow_role(host_states, flow.responder_ip, flow, "responder", flow.initiator_ip)

    profiles = []
    for host_ip, state in sorted(host_states.items()):
        metrics = compute_host_metrics(host_ip, state)
        inferred_role, role_confidence, role_evidence = infer_host_role(metrics, state)
        risk_score, confidence, indicators, indicator_details, severity = score_host_behavior(
            metrics,
            state,
            inferred_role,
        )
        graph_node = _build_graph_node(host_ip, metrics, risk_score, confidence, severity)
        profile = HostProfile(
            ip_address=host_ip,
            **metrics,
            inferred_role=inferred_role,
            role_confidence=role_confidence,
            role_evidence=role_evidence,
            risk_score=risk_score,
            confidence=confidence,
            severity=severity,
            behavioral_indicators=indicators,
            indicator_details=indicator_details,
            graph_node_size=graph_node.node_size,
            graph_risk_color=graph_node.node_color,
            graph_cluster_group=graph_node.cluster_group,
            graph_node=graph_node.model_dump(),
        )
        profile.baseline_state = normalize_host_state(profile)
        profiles.append(profile)

    return profiles


def _apply_self_flow(host_states: Dict[str, Dict], flow):
    state = host_states.setdefault(flow.initiator_ip, _new_host_state())
    state["flows"].append(flow)
    state["roles"]["initiator"] += 1
    state["roles"]["responder"] += 1
    state["peers"].add(flow.responder_ip)
    state["destinations"].add(flow.responder_ip)
    state["protocols"].add(flow.application_protocol)
    state["transports"].add(flow.transport_layer)
    state["peer_flows"][flow.responder_ip].append(flow)
    if flow.responder_port is not None:
        state["ports"].add(flow.responder_port)
        state["service_ports"].add(flow.responder_port)
    _count_host_direction(state, flow.direction)
    _update_temporal_state(state, flow)


def _apply_flow_role(host_states: Dict[str, Dict], host_ip: str, flow, role: str, peer_ip: str):
    state = host_states.setdefault(host_ip, _new_host_state())
    state["flows"].append(flow)
    state["roles"][role] += 1
    state["peers"].add(peer_ip)
    state["protocols"].add(flow.application_protocol)
    state["transports"].add(flow.transport_layer)
    state["peer_flows"][peer_ip].append(flow)

    if role == "initiator":
        state["destinations"].add(flow.responder_ip)
        if flow.responder_port is not None:
            state["ports"].add(flow.responder_port)
            state["remote_ports"].add(flow.responder_port)
        _count_host_direction(state, flow.direction)
    else:
        if flow.responder_port is not None:
            state["ports"].add(flow.responder_port)
            state["service_ports"].add(flow.responder_port)
        _count_host_direction(state, _responder_direction(flow.direction))

    _update_temporal_state(state, flow)


def _new_host_state() -> Dict:
    return {
        "flows": [],
        "roles": defaultdict(int),
        "directions": defaultdict(int),
        "destinations": set(),
        "peers": set(),
        "ports": set(),
        "service_ports": set(),
        "remote_ports": set(),
        "protocols": set(),
        "transports": set(),
        "peer_flows": defaultdict(list),
        "first_seen": None,
        "last_seen": None,
        "first_seen_sequence": 0,
        "last_seen_sequence": 0,
        "first_timeline_index": 0,
        "last_timeline_index": 0,
        "time_buckets": set(),
        "hourly_activity": defaultdict(int),
    }


def _count_host_direction(state: Dict, direction: str):
    if direction in {"outbound", "inbound", "internal", "external", "broadcast", "multicast", "loopback", "unknown"}:
        state["directions"][direction] += 1
    else:
        state["directions"]["unknown"] += 1


def _responder_direction(direction: str) -> str:
    if direction == "outbound":
        return "inbound"
    if direction == "inbound":
        return "outbound"
    return direction


def _update_temporal_state(state: Dict, flow):
    first_seen = _parse_timestamp(flow.timestamp_first)
    last_seen = _parse_timestamp(flow.timestamp_last)

    if state["first_seen"] is None or first_seen < state["first_seen"]:
        state["first_seen"] = first_seen
        state["first_seen_sequence"] = flow.first_seen_sequence
        state["first_timeline_index"] = getattr(flow, "first_timeline_index", flow.first_seen_sequence)

    if state["last_seen"] is None or last_seen > state["last_seen"]:
        state["last_seen"] = last_seen
        state["last_seen_sequence"] = flow.last_seen_sequence
        state["last_timeline_index"] = getattr(flow, "last_timeline_index", flow.last_seen_sequence)

    for timestamp in (first_seen, last_seen):
        bucket = timestamp.replace(minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
        state["time_buckets"].add(bucket)
        state["hourly_activity"][bucket] += 1


def _build_graph_node(host_ip: str, metrics: Dict, risk_score: float, confidence: float, severity: str) -> HostGraphNode:
    return HostGraphNode(
        id=host_ip,
        risk_score=risk_score,
        confidence=confidence,
        connections=metrics["unique_peers"],
        protocols=metrics["protocols"],
        node_size=_node_size(metrics, risk_score),
        node_color=_risk_color(risk_score, confidence),
        cluster_group=_cluster_group(metrics, severity),
        first_seen=metrics["first_seen"],
        last_seen=metrics["last_seen"],
        metadata={
            "flow_count": metrics["flow_count"],
            "external_flow_count": metrics["external_flow_count"],
            "external_unique_hosts": metrics["external_unique_hosts"],
            "suspicious_flow_count": metrics["suspicious_flow_count"],
            "graph_importance": metrics["graph_importance"],
        },
    )


def _node_size(metrics: Dict, risk_score: float) -> float:
    return round(min(8 + metrics["graph_degree"] * 0.35 + risk_score / 8, 42), 2)


def _risk_color(risk_score: float, confidence: float) -> str:
    adjusted_score = risk_score * confidence
    if adjusted_score >= 55:
        return "#d95f3d"
    if adjusted_score >= 30:
        return "#ffb347"
    if risk_score > 0:
        return "#f0d878"
    return "#7aa6c2"


def _cluster_group(metrics: Dict, severity: str) -> str:
    if metrics["external_connections"] and severity in {"medium", "high"}:
        return "elevated_external_behavior"
    if set(metrics["protocols"]).issubset({"arp", "dhcp", "llmnr", "mdns", "nbns", "ssdp"}):
        return "infrastructure_chatter"
    if metrics["internal_connections"] and not metrics["external_connections"]:
        return "internal_host"
    return "mixed_behavior"


def _parse_timestamp(timestamp: str) -> datetime:
    parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
    return parsed_timestamp.astimezone(timezone.utc)
