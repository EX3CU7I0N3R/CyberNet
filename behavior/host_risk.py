from typing import Dict, List


MAX_CONFIDENCE = 0.85
INFRASTRUCTURE_PROTOCOLS = {"arp", "dhcp", "llmnr", "mdns", "nbns", "ssdp"}


def score_host_behavior(metrics: Dict, state: Dict) -> tuple[float, float, List[str], Dict[str, float], str]:
    positive_indicators = _positive_indicators(metrics, state)
    negative_pressure = _negative_pressure(metrics)
    raw_score = max(sum(positive_indicators.values()) - negative_pressure, 0.0)
    risk_score = round(min(raw_score, 100.0), 2)
    confidence = _confidence(metrics, state)
    severity = _severity(risk_score, confidence)
    return risk_score, confidence, list(positive_indicators), positive_indicators, severity


def _positive_indicators(metrics: Dict, state: Dict) -> Dict[str, float]:
    indicators = {}

    if metrics["persistent_connection_count"] and metrics["external_connections"]:
        indicators["unusual_communication_persistence"] = min(metrics["persistent_connection_count"] * 10, 24)

    if metrics["beacon_flow_count"]:
        indicators["periodic_external_communication"] = min(metrics["beacon_flow_count"] * 14, 32)

    if metrics["unique_destinations"] >= 25:
        indicators["elevated_destination_fanout"] = min(metrics["unique_destinations"] / 50 * 22, 22)

    if _has_unusual_protocol(metrics):
        indicators["unusual_protocol_usage"] = 12

    if metrics["upload_bytes"] > 1_000_000 and metrics["upload_download_ratio"] >= 3:
        indicators["asymmetric_upload_behavior"] = 18

    if _has_persistent_tls(state):
        indicators["persistent_external_tls"] = 18

    rare_destination_count = sum(
        1 for flow in state["flows"]
        if "rare_destination_observed" in getattr(flow, "suspicious_indicators", [])
    )
    if rare_destination_count:
        indicators["rare_destination_behavior"] = min(rare_destination_count * 8, 20)

    if metrics["suspicious_flow_count"]:
        indicators["elevated_flow_behavioral_risk"] = min(metrics["suspicious_flow_count"] * 10, 30)

    return {key: round(value, 4) for key, value in indicators.items()}


def _negative_pressure(metrics: Dict) -> float:
    if not metrics["flow_count"]:
        return 0.0

    suppressed_ratio = metrics["suppressed_flow_count"] / metrics["flow_count"]
    infrastructure_only = set(metrics["protocols"]).issubset(INFRASTRUCTURE_PROTOCOLS)
    reduction = min(suppressed_ratio * 35, 35)

    if infrastructure_only:
        reduction += 35

    if metrics["external_connections"] == 0 and metrics["suspicious_flow_count"] == 0:
        reduction += 15

    return reduction


def _confidence(metrics: Dict, state: Dict) -> float:
    flow_quality = min(metrics["flow_count"] / 75, 1.0)
    sample_quality = min(metrics["packet_count"] / 1000, 1.0)
    duration_quality = min(metrics["active_duration"] / 7200, 1.0)
    protocol_reliability = _protocol_reliability(state)
    stability = _metric_stability(metrics)

    confidence = (
        flow_quality * 0.25
        + sample_quality * 0.20
        + duration_quality * 0.20
        + protocol_reliability * 0.20
        + stability * 0.15
    )
    return round(min(confidence, MAX_CONFIDENCE), 4)


def _protocol_reliability(state: Dict) -> float:
    flows = state["flows"]
    if not flows:
        return 0.0
    return sum(max(min(getattr(flow, "app_confidence", 0.0), 0.95), 0.2) for flow in flows) / len(flows)


def _metric_stability(metrics: Dict) -> float:
    if metrics["flow_count"] < 3:
        return 0.25
    if metrics["active_duration"] <= 0:
        return 0.35
    density = metrics["activity_density"]
    if density <= 1:
        return 0.55
    if density <= 10:
        return 0.75
    return 0.65


def _has_unusual_protocol(metrics: Dict) -> bool:
    protocols = set(metrics["protocols"])
    if "unknown" in protocols:
        return True
    expected_protocols = {"arp", "dhcp", "dns", "http", "https", "icmp", "llmnr", "mdns", "nbns", "smb", "ssdp"}
    return bool(protocols - expected_protocols)


def _has_persistent_tls(state: Dict) -> bool:
    for flow in state["flows"]:
        if flow.application_protocol != "https":
            continue
        if flow.direction not in {"outbound", "inbound", "external"}:
            continue
        if getattr(flow, "raw_duration_seconds", 0.0) >= 300 or getattr(flow, "beacon_score", 0.0):
            return True
    return False


def _severity(score: float, confidence: float) -> str:
    adjusted_score = score * confidence
    if adjusted_score >= 55:
        return "high"
    if adjusted_score >= 30:
        return "medium"
    if score > 0:
        return "low"
    return "informational"
