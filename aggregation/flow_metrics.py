from datetime import datetime, timezone
from math import log2, sqrt
from statistics import mean, median, stdev
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from aggregation.suppression import SuppressionPolicy


class EnrichedFlow(BaseModel):
    flow_id: str
    initiator_ip: str
    responder_ip: str
    transport_layer: str
    initiator_port: Optional[int] = None
    responder_port: Optional[int] = None
    initiator_packets: int
    initiator_bytes: int
    responder_packets: int
    responder_bytes: int
    packet_count: int
    direction: str
    timestamp_first: str
    timestamp_last: str
    first_seen_sequence: int = 0
    last_seen_sequence: int = 0
    application_protocol: str
    app_confidence: float
    syn_count: int = 0
    ack_count: int = 0
    rst_count: int = 0
    fin_count: int = 0
    psh_count: int = 0
    urg_count: int = 0
    tcp_state_summary: str = "not_tcp"
    chronology_valid: bool = True
    duration_anomalies: List[str] = Field(default_factory=list)

    duration_seconds: float
    raw_duration_seconds: float = 0.0
    packets_per_second: float
    bytes_per_second: float
    avg_packet_size: float
    packet_size_variance: float
    packet_size_cv: float = 0.0

    mean_inter_packet_delay_ms: Optional[float] = None
    median_inter_packet_delay_ms: Optional[float] = None
    max_inter_packet_delay_ms: Optional[float] = None
    inter_arrival_jitter: Optional[float] = None
    beacon_intervals: Optional[int] = None

    payload_entropy: float = 0.0
    port_entropy: float = 0.0
    protocol_diversity: int = 0
    data_ratio: float = 0.0

    suppressed: bool = False
    suppression_reason: str = ""
    suppression_category: str = ""
    beacon_score: Optional[float] = None
    beacon_confidence: Optional[float] = None
    beacon_reason: str = ""
    behavioral_score: float = 0.0
    confidence: float = 0.0
    severity: str = "informational"
    is_suspicious: bool = False
    suspicious_indicators: List[str] = Field(default_factory=list)
    indicator_details: Dict[str, float] = Field(default_factory=dict)


class StatisticsModule:
    @staticmethod
    def compute_packet_size_stats(packet_sizes: List[int]) -> Dict:
        if not packet_sizes:
            return {
                "avg_packet_size": 0.0,
                "packet_size_variance": 0.0,
                "packet_size_stddev": 0.0,
                "packet_size_cv": 0.0,
            }

        avg_packet_size = mean(packet_sizes)
        variance = sum((size - avg_packet_size) ** 2 for size in packet_sizes) / len(packet_sizes)
        stddev_value = sqrt(variance) if len(packet_sizes) > 1 else 0.0
        packet_size_cv = stddev_value / avg_packet_size if avg_packet_size else 0.0

        return {
            "avg_packet_size": round(avg_packet_size, 2),
            "packet_size_variance": round(variance, 2),
            "packet_size_stddev": round(stddev_value, 2),
            "packet_size_cv": round(packet_size_cv, 4),
        }

    @staticmethod
    def compute_throughput_stats(packet_count: int, total_bytes: int, duration: float) -> Dict:
        duration_floored = max(duration, 0.001)
        return {
            "packets_per_second": round(min(packet_count / duration_floored, 100000), 4),
            "bytes_per_second": round(min(total_bytes / duration_floored, 1_000_000_000), 4),
        }


class TimingModule:
    @staticmethod
    def compute_inter_packet_delays(timestamps: List[datetime]) -> Dict:
        if len(timestamps) < 2:
            return _empty_timing()

        ordered_timestamps = sorted(timestamps)
        delays_ms = [
            (ordered_timestamps[index] - ordered_timestamps[index - 1]).total_seconds() * 1000
            for index in range(1, len(ordered_timestamps))
        ]
        valid_delays_ms = [delay for delay in delays_ms if delay >= 0]
        if len(valid_delays_ms) != len(delays_ms) or not valid_delays_ms:
            timing = _empty_timing()
            timing["timing_anomaly"] = "negative_inter_packet_delay"
            return timing

        jitter_ms = stdev(valid_delays_ms) if len(valid_delays_ms) > 1 else 0.0
        return {
            "mean_ipd_ms": round(mean(valid_delays_ms), 4),
            "median_ipd_ms": round(median(valid_delays_ms), 4),
            "max_ipd_ms": round(max(valid_delays_ms), 4),
            "ipd_jitter_ms": round(jitter_ms, 4),
            "ipd_intervals": len(valid_delays_ms),
            "timing_anomaly": "",
        }


class EntropyModule:
    @staticmethod
    def shannon_entropy(values: List[int]) -> float:
        if not values:
            return 0.0

        frequencies = {}
        for value in values:
            frequencies[value] = frequencies.get(value, 0) + 1

        total = len(values)
        entropy = 0.0
        for count in frequencies.values():
            probability = count / total
            entropy -= probability * log2(probability)

        return round(entropy, 4)


class HeuristicsModule:
    MIN_BEACON_PACKETS = 20
    MIN_BEACON_INTERVALS = 10

    @staticmethod
    def compute_beacon_score(flow, timing: Dict, packet_size_cv: float) -> tuple[Optional[float], Optional[float], str]:
        if flow.packet_count < HeuristicsModule.MIN_BEACON_PACKETS:
            return None, None, f"insufficient_packets ({flow.packet_count} < {HeuristicsModule.MIN_BEACON_PACKETS})"

        interval_count = timing.get("ipd_intervals", 0)
        if interval_count < HeuristicsModule.MIN_BEACON_INTERVALS:
            return None, None, f"insufficient_intervals ({interval_count} < {HeuristicsModule.MIN_BEACON_INTERVALS})"

        mean_ipd_ms = timing.get("mean_ipd_ms")
        jitter_ms = timing.get("ipd_jitter_ms")
        if mean_ipd_ms is None or jitter_ms is None or mean_ipd_ms <= 0:
            return None, None, "missing_timing_data"

        interval_cv = jitter_ms / mean_ipd_ms
        timing_consistency = max(0.0, 1.0 - min(interval_cv, 1.5) / 1.5)
        payload_consistency = max(0.0, 1.0 - min(packet_size_cv, 1.5) / 1.5)
        beacon_score = (timing_consistency * 0.7) + (payload_consistency * 0.3)
        confidence = HeuristicsModule.compute_confidence(
            interval_count=interval_count,
            duration_seconds=flow.raw_duration_seconds,
            interval_cv=interval_cv,
            app_confidence=flow.app_confidence,
            packet_count=flow.packet_count,
        )

        return round(beacon_score, 4), confidence, f"periodicity_cv={interval_cv:.2f};payload_cv={packet_size_cv:.2f}"

    @staticmethod
    def compute_confidence(
        interval_count: int,
        duration_seconds: float,
        interval_cv: float,
        app_confidence: float,
        packet_count: int,
    ) -> float:
        sample_quality = min(interval_count / 50, 1.0)
        duration_quality = min(max(duration_seconds, 0) / 3600, 1.0)
        variance_quality = max(0.0, 1.0 - min(interval_cv, 2.0) / 2.0)
        protocol_quality = min(max(app_confidence, 0.2), 0.95)
        sufficiency_quality = min(packet_count / 100, 1.0)

        encrypted_visibility_decay = 0.88 if app_confidence >= 0.85 else 1.0
        confidence = (
            sample_quality * 0.30
            + duration_quality * 0.20
            + variance_quality * 0.20
            + protocol_quality * 0.15
            + sufficiency_quality * 0.15
        ) * encrypted_visibility_decay
        return round(min(confidence, 0.82), 4)

    @staticmethod
    def compute_behavioral_risk(flow, timing: Dict, beacon_score: Optional[float], rarity_context: Dict) -> tuple[float, List[str], Dict[str, float]]:
        indicators = {}

        if beacon_score is not None and beacon_score >= 0.65:
            indicators["potential_beaconing_behavior"] = beacon_score * 30

        if flow.raw_duration_seconds >= 300 and flow.packet_count >= 10 and flow.packets_per_second < 0.2:
            indicators["periodic_low_volume_communication"] = 18

        if flow.direction in {"outbound", "inbound", "external"}:
            indicators["external_communication"] = 12

        destination_flow_count = rarity_context["destination_counts"].get(flow.responder_ip, 0)
        if flow.direction in {"outbound", "external"} and destination_flow_count <= 2:
            indicators["low_frequency_destination"] = 12

        protocol_flow_count = rarity_context["protocol_counts"].get(flow.application_protocol, 0)
        if flow.application_protocol in {"unknown", "irc"} or protocol_flow_count <= 2:
            indicators["unusual_protocol_context"] = 10

        if flow.responder_port in {4444, 5555, 6667, 8888, 1337, 31337, 27374, 12345}:
            indicators["unusual_remote_service_port"] = 18

        if flow.initiator_bytes > 1_000_000 and flow.data_ratio < 0.25:
            indicators["upload_heavy_asymmetry"] = 16

        if flow.transport_layer == "tcp" and flow.tcp_state_summary in {"syn_without_ack", "reset_observed"}:
            indicators[f"tcp_{flow.tcp_state_summary}"] = 12

        indicator_names = list(indicators)
        if len(indicator_names) < 2:
            return 0.0, [], {}

        risk_score = min(sum(indicators.values()), 100.0)
        return round(risk_score, 2), indicator_names, {key: round(value, 4) for key, value in indicators.items()}


def compute_flow_metrics(
    canonical_events: List,
    directional_flows: Dict,
    suppression_policy: Optional[SuppressionPolicy] = None,
) -> List[EnrichedFlow]:
    suppression_policy = suppression_policy or SuppressionPolicy()
    events_by_flow = {}
    for event in canonical_events:
        if event is not None:
            events_by_flow.setdefault(event.flow_id, []).append(event)

    rarity_context = {
        "destination_counts": _count_by(directional_flows.values(), "responder_ip"),
        "protocol_counts": _count_by(directional_flows.values(), "application_protocol"),
    }

    enriched_flows = []
    for flow_id, flow in directional_flows.items():
        events = sorted(events_by_flow.get(flow_id, []), key=lambda event: event.replay_sequence_id)
        packet_sizes = [event.total_bytes for event in events]
        ports = [port for event in events for port in (event.src_port, event.dst_port) if port is not None]
        timestamps = [_parse_timestamp(event.timestamp) for event in events if event.timestamp]

        stats = StatisticsModule.compute_packet_size_stats(packet_sizes)
        throughput = StatisticsModule.compute_throughput_stats(
            flow.packet_count,
            flow.initiator_bytes + flow.responder_bytes,
            flow.duration_seconds,
        )
        timing = TimingModule.compute_inter_packet_delays(timestamps)
        data_ratio = _compute_data_ratio(flow.initiator_bytes, flow.responder_bytes)

        flow.data_ratio = data_ratio
        suppression = suppression_policy.evaluate_flow(flow)

        beacon_score = None
        beacon_confidence = None
        beacon_reason = suppression.reason if suppression.suppressed else ""
        behavioral_score = 0.0
        confidence = 0.0
        suspicious_indicators = []
        indicator_details = {}

        if not suppression.suppressed:
            beacon_score, beacon_confidence, beacon_reason = HeuristicsModule.compute_beacon_score(
                flow,
                timing,
                stats["packet_size_cv"],
            )
            behavioral_score, suspicious_indicators, indicator_details = HeuristicsModule.compute_behavioral_risk(
                flow,
                timing,
                beacon_score,
                rarity_context,
            )
            confidence = beacon_confidence or _weak_signal_confidence(flow, timing)

        enriched_flows.append(EnrichedFlow(
            flow_id=flow.flow_id,
            initiator_ip=flow.initiator_ip,
            responder_ip=flow.responder_ip,
            transport_layer=flow.transport_layer,
            initiator_port=flow.initiator_port,
            responder_port=flow.responder_port,
            initiator_packets=flow.initiator_packets,
            initiator_bytes=flow.initiator_bytes,
            responder_packets=flow.responder_packets,
            responder_bytes=flow.responder_bytes,
            packet_count=flow.packet_count,
            direction=flow.direction,
            timestamp_first=flow.timestamp_first,
            timestamp_last=flow.timestamp_last,
            first_seen_sequence=flow.first_seen_sequence,
            last_seen_sequence=flow.last_seen_sequence,
            application_protocol=flow.application_protocol,
            app_confidence=flow.app_confidence,
            syn_count=flow.syn_count,
            ack_count=flow.ack_count,
            rst_count=flow.rst_count,
            fin_count=flow.fin_count,
            psh_count=flow.psh_count,
            urg_count=flow.urg_count,
            tcp_state_summary=flow.tcp_state_summary,
            chronology_valid=flow.chronology_valid,
            duration_anomalies=flow.duration_anomalies,
            duration_seconds=flow.duration_seconds,
            raw_duration_seconds=flow.raw_duration_seconds,
            packets_per_second=throughput["packets_per_second"],
            bytes_per_second=throughput["bytes_per_second"],
            avg_packet_size=stats["avg_packet_size"],
            packet_size_variance=stats["packet_size_variance"],
            packet_size_cv=stats["packet_size_cv"],
            mean_inter_packet_delay_ms=timing.get("mean_ipd_ms"),
            median_inter_packet_delay_ms=timing.get("median_ipd_ms"),
            max_inter_packet_delay_ms=timing.get("max_ipd_ms"),
            inter_arrival_jitter=timing.get("ipd_jitter_ms"),
            beacon_intervals=timing.get("ipd_intervals"),
            payload_entropy=EntropyModule.shannon_entropy(packet_sizes),
            port_entropy=EntropyModule.shannon_entropy(ports),
            protocol_diversity=1 if flow.application_protocol else 0,
            data_ratio=data_ratio,
            suppressed=suppression.suppressed,
            suppression_reason=suppression.reason,
            suppression_category=suppression.category,
            beacon_score=beacon_score,
            beacon_confidence=beacon_confidence,
            beacon_reason=beacon_reason,
            behavioral_score=behavioral_score,
            confidence=confidence,
            severity=_severity(behavioral_score, confidence),
            is_suspicious=behavioral_score >= 35 and confidence >= 0.20,
            suspicious_indicators=suspicious_indicators,
            indicator_details=indicator_details,
        ))

    return enriched_flows


def _empty_timing() -> Dict:
    return {
        "mean_ipd_ms": None,
        "median_ipd_ms": None,
        "max_ipd_ms": None,
        "ipd_jitter_ms": None,
        "ipd_intervals": 0,
        "timing_anomaly": "",
    }


def _parse_timestamp(timestamp: str) -> datetime:
    parsed_timestamp = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed_timestamp.tzinfo is None:
        parsed_timestamp = parsed_timestamp.replace(tzinfo=timezone.utc)
    return parsed_timestamp.astimezone(timezone.utc)


def _compute_data_ratio(initiator_bytes: int, responder_bytes: int) -> float:
    if initiator_bytes <= 0:
        return 0.0
    return round(responder_bytes / initiator_bytes, 4)


def _count_by(flows, attribute: str) -> Dict:
    counts = {}
    for flow in flows:
        key = getattr(flow, attribute)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _weak_signal_confidence(flow, timing: Dict) -> float:
    interval_quality = min(timing.get("ipd_intervals", 0) / 30, 1.0)
    duration_quality = min(max(flow.raw_duration_seconds, 0) / 1800, 1.0)
    packet_quality = min(flow.packet_count / 50, 1.0)
    confidence = (interval_quality * 0.35) + (duration_quality * 0.25) + (packet_quality * 0.25) + 0.10
    return round(min(confidence, 0.70), 4)


def _severity(score: float, confidence: float) -> str:
    adjusted_score = score * confidence
    if adjusted_score >= 55:
        return "high"
    if adjusted_score >= 30:
        return "medium"
    if score > 0:
        return "low"
    return "informational"
