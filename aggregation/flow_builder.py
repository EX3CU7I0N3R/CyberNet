from datetime import datetime, timezone
from typing import Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field


class DirectionalFlow(BaseModel):
    flow_id: str
    timestamp_first: str
    timestamp_last: str
    first_seen_sequence: int = 0
    last_seen_sequence: int = 0
    initiator_ip: str
    responder_ip: str
    transport_layer: str
    initiator_port: Optional[int] = None
    responder_port: Optional[int] = None
    initiator_packets: int = 0
    initiator_bytes: int = 0
    responder_packets: int = 0
    responder_bytes: int = 0
    syn_count: int = 0
    ack_count: int = 0
    rst_count: int = 0
    fin_count: int = 0
    psh_count: int = 0
    urg_count: int = 0
    tcp_state_summary: str = "not_tcp"
    application_protocol: str
    app_confidence: float
    direction: str
    packet_count: int = 0
    duration_seconds: float = 0.0
    raw_duration_seconds: float = 0.0
    packets_per_second: float = 0.0
    mean_inter_packet_delay_ms: float = 0.0
    max_inter_packet_delay_ms: float = 0.0
    data_ratio: float = 0.0
    chronology_valid: bool = True
    duration_anomalies: List[str] = Field(default_factory=list)


def build_flows(canonical_events: List) -> Dict[str, DirectionalFlow]:
    flows: Dict[str, DirectionalFlow] = {}

    for event in sorted((event for event in canonical_events if event is not None), key=_event_order_key):
        flow_id = event.flow_id

        if flow_id not in flows:
            flows[flow_id] = DirectionalFlow(
                flow_id=flow_id,
                timestamp_first=event.timestamp,
                timestamp_last=event.timestamp,
                first_seen_sequence=event.replay_sequence_id,
                last_seen_sequence=event.replay_sequence_id,
                initiator_ip=event.src_ip,
                responder_ip=event.dst_ip,
                transport_layer=event.transport_layer,
                initiator_port=event.src_port,
                responder_port=event.dst_port,
                application_protocol=event.application_protocol,
                app_confidence=event.app_confidence,
                direction=event.direction,
            )

        flow = flows[flow_id]
        event_timestamp = _parse_timestamp(event.timestamp)

        if event_timestamp < _parse_timestamp(flow.timestamp_first):
            flow.timestamp_first = event.timestamp
            flow.first_seen_sequence = event.replay_sequence_id

        if event_timestamp > _parse_timestamp(flow.timestamp_last):
            flow.timestamp_last = event.timestamp
            flow.last_seen_sequence = event.replay_sequence_id

        if event.src_ip == flow.initiator_ip:
            flow.initiator_packets += 1
            flow.initiator_bytes += event.total_bytes
        else:
            flow.responder_packets += 1
            flow.responder_bytes += event.total_bytes

        _aggregate_tcp_flags(flow, event.tcp_flags)
        flow.packet_count += 1

    for flow in flows.values():
        _compute_flow_metrics(flow)

    return flows


def flows_to_dataframe(flows: Dict[str, DirectionalFlow]) -> pd.DataFrame:
    return pd.DataFrame([flow.model_dump() for flow in flows.values()])


def get_bidirectional_view(flows: Dict[str, DirectionalFlow]) -> List[Dict]:
    endpoints_to_flows = {}

    for flow in flows.values():
        endpoints = tuple(sorted([
            (flow.initiator_ip, flow.initiator_port),
            (flow.responder_ip, flow.responder_port),
        ]))
        endpoints_to_flows.setdefault(endpoints, []).append(flow)

    bidirectional_flows = []
    for endpoints, directional_flows in endpoints_to_flows.items():
        bidirectional_flows.append({
            "endpoints": endpoints,
            "ip_a": endpoints[0][0],
            "port_a": endpoints[0][1],
            "ip_b": endpoints[1][0],
            "port_b": endpoints[1][1],
            "total_packets": sum(flow.packet_count for flow in directional_flows),
            "total_bytes": sum(flow.initiator_bytes + flow.responder_bytes for flow in directional_flows),
            "timestamp_first": min(flow.timestamp_first for flow in directional_flows),
            "timestamp_last": max(flow.timestamp_last for flow in directional_flows),
            "directional_flows": len(directional_flows),
        })

    return bidirectional_flows


def _aggregate_tcp_flags(flow: DirectionalFlow, tcp_flags: Dict[str, bool]):
    if not tcp_flags:
        return

    if tcp_flags.get("syn"):
        flow.syn_count += 1
    if tcp_flags.get("ack"):
        flow.ack_count += 1
    if tcp_flags.get("rst"):
        flow.rst_count += 1
    if tcp_flags.get("fin"):
        flow.fin_count += 1
    if tcp_flags.get("psh"):
        flow.psh_count += 1
    if tcp_flags.get("urg"):
        flow.urg_count += 1


def _compute_flow_metrics(flow: DirectionalFlow):
    try:
        duration = (_parse_timestamp(flow.timestamp_last) - _parse_timestamp(flow.timestamp_first)).total_seconds()
    except Exception:
        flow.chronology_valid = False
        flow.duration_anomalies.append("timestamp_parse_failure")
        duration = 0.0

    flow.raw_duration_seconds = duration

    if duration < 0:
        flow.chronology_valid = False
        flow.duration_anomalies.append("negative_duration")
        duration = 0.0

    if duration > 31_536_000:
        flow.duration_anomalies.append("duration_exceeds_one_year")

    duration_floored = max(duration, 0.001)
    flow.duration_seconds = duration_floored
    flow.packets_per_second = min(flow.packet_count / duration_floored, 100000)
    flow.tcp_state_summary = _summarize_tcp_state(flow)


def _summarize_tcp_state(flow: DirectionalFlow) -> str:
    if flow.transport_layer != "tcp":
        return "not_tcp"
    if flow.rst_count:
        return "reset_observed"
    if flow.syn_count and not flow.ack_count:
        return "syn_without_ack"
    if flow.syn_count and flow.ack_count and flow.fin_count:
        return "closed"
    if flow.syn_count and flow.ack_count:
        return "established_observed"
    return "tcp_flags_observed"


def _event_order_key(event) -> tuple[datetime, int]:
    try:
        timestamp = _parse_timestamp(event.timestamp)
    except Exception:
        timestamp = datetime.min.replace(tzinfo=timezone.utc)

    return timestamp, getattr(event, "replay_sequence_id", getattr(event, "packet_index", 0))


def _parse_timestamp(timestamp: str) -> datetime:
    parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
    return parsed_timestamp.astimezone(timezone.utc)
