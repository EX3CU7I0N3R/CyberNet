from math import exp
from typing import Dict, List

from behavior.role_manager import DOMAIN_CONTROLLER, INFRASTRUCTURE, SERVER, WORKSTATION, normalize_role


BEHAVIOR_ONLY_SOFT_CAP = 82.0
MAX_CONFIDENCE = 0.78
INFRASTRUCTURE_PROTOCOLS = {"arp", "dhcp", "llmnr", "mdns", "nbns", "ssdp"}


def score_host_behavior(
    metrics: Dict,
    state: Dict,
    inferred_role: str = "unknown",
) -> tuple[float, float, List[str], Dict[str, float], str]:
    inferred_role = normalize_role(inferred_role)
    positive_indicators = _positive_indicators(metrics, state, inferred_role)
    negative_pressure = _negative_pressure(metrics, inferred_role)
    pressure = max(sum(positive_indicators.values()) - negative_pressure, 0.0)
    risk_score = _bounded_risk(pressure, positive_indicators, inferred_role)
    confidence = _confidence(metrics, state)
    severity = _severity(risk_score, confidence)
    return risk_score, confidence, list(positive_indicators), positive_indicators, severity


def _positive_indicators(metrics: Dict, state: Dict, inferred_role: str) -> Dict[str, float]:
    indicators = {}

    if metrics["persistent_relationships"] and metrics["external_unique_hosts"]:
        indicators["unusual_external_persistence"] = min(metrics["persistent_relationships"] * 8, 20)

    if metrics["beacon_flow_count"]:
        indicators["periodic_communication_behavior"] = min(metrics["beacon_flow_count"] * 10, 24)

    if metrics["external_unique_hosts"] >= 12:
        indicators["elevated_external_relationship_fanout"] = min(metrics["external_unique_hosts"] / 35 * 18, 18)

    if metrics["activity_cluster_count"] >= 3 and metrics["active_duration"] >= 1800:
        indicators["recurring_activity_windows"] = min(metrics["activity_cluster_count"] * 4, 14)

    if _has_unusual_protocol(metrics, inferred_role):
        indicators["ambiguous_or_unusual_protocol_mix"] = 10

    if metrics["upload_bytes"] > 1_000_000 and metrics["upload_download_ratio"] >= 3:
        indicators["asymmetric_upload_behavior"] = 14

    if _has_persistent_tls(state):
        indicators["persistent_external_tls"] = 14

    low_frequency_count = sum(
        1 for flow in state["flows"]
        if (
            "low_frequency_destination" in getattr(flow, "suspicious_indicators", [])
            or "rare_destination_observed" in getattr(flow, "suspicious_indicators", [])
        )
    )
    if low_frequency_count:
        indicators["infrequent_external_contact"] = min(low_frequency_count * 6, 16)

    if metrics["suspicious_flow_count"]:
        indicators["elevated_flow_context"] = min(metrics["suspicious_flow_count"] * 7, 20)

    concentration = _relationship_concentration(state)
    if concentration >= 0.70 and metrics["external_unique_hosts"]:
        indicators["concentrated_external_relationship"] = 8

    if inferred_role == WORKSTATION and _external_smb_observed(state):
        indicators["workstation_external_smb_exposure"] = 16

    return {key: round(value, 4) for key, value in indicators.items()}


def _bounded_risk(pressure: float, indicators: Dict[str, float], inferred_role: str) -> float:
    cap = BEHAVIOR_ONLY_SOFT_CAP
    if inferred_role == INFRASTRUCTURE:
        cap = 42.0
    if len(indicators) <= 1:
        cap = min(cap, 48.0)
    elif len(indicators) == 2:
        cap = min(cap, 64.0)

    normalized_score = cap * (1 - exp(-pressure / 48))
    return round(min(normalized_score, cap), 2)


def _negative_pressure(metrics: Dict, inferred_role: str) -> float:
    if not metrics["flow_count"]:
        return 0.0

    suppressed_ratio = metrics["suppressed_flow_count"] / metrics["flow_count"]
    infrastructure_only = set(metrics["protocols"]).issubset(INFRASTRUCTURE_PROTOCOLS)
    reduction = min(suppressed_ratio * 40, 38)

    if infrastructure_only:
        reduction += 34
    if inferred_role in {DOMAIN_CONTROLLER, SERVER} and "smb" in metrics["protocols"]:
        reduction += 8
    if inferred_role == INFRASTRUCTURE:
        reduction += 18
    if metrics["external_unique_hosts"] == 0 and metrics["suspicious_flow_count"] == 0:
        reduction += 14

    return reduction


def _confidence(metrics: Dict, state: Dict) -> float:
    flow_quality = min(metrics["flow_count"] / 85, 1.0)
    sample_quality = min(metrics["packet_count"] / 1500, 1.0)
    duration_quality = min(metrics["active_duration"] / 10800, 1.0)
    protocol_reliability = _protocol_reliability(metrics, state)
    completeness = metrics["telemetry_completeness"]
    stability = _metric_stability(metrics)

    uncertainty_decay = 1 - min(metrics["unknown_protocol_ratio"] * 0.55, 0.55)
    encryption_decay = 1 - min(metrics["encrypted_flow_ratio"] * 0.18, 0.18)

    confidence = (
        flow_quality * 0.18
        + sample_quality * 0.18
        + duration_quality * 0.18
        + protocol_reliability * 0.18
        + completeness * 0.18
        + stability * 0.10
    )
    confidence *= uncertainty_decay * encryption_decay
    return round(min(confidence, MAX_CONFIDENCE), 4)


def _protocol_reliability(metrics: Dict, state: Dict) -> float:
    flows = state["flows"]
    if not flows:
        return 0.0
    visibility = 1 - min(metrics["unknown_protocol_ratio"], 0.9)
    return metrics["protocol_confidence_avg"] * visibility


def _metric_stability(metrics: Dict) -> float:
    if metrics["flow_count"] < 3:
        return 0.22
    if metrics["active_duration"] <= 0:
        return 0.30
    if metrics["activity_cluster_count"] <= 1:
        return 0.48
    if metrics["activity_density"] <= 10:
        return 0.68
    return 0.58


def _has_unusual_protocol(metrics: Dict, inferred_role: str) -> bool:
    protocols = set(metrics["protocols"])
    expected_protocols = {
        "arp", "dhcp", "dns", "ftp", "http", "http2", "https", "icmp", "imap", "imaps",
        "kerberos", "ldap", "ldaps", "llmnr", "mdns", "msrpc", "nbns", "netbios_datagram",
        "netbios_session", "ntp", "pop", "pops", "rdp", "smb", "smtp", "smtp_submission",
        "smtps", "snmp", "snmptrap", "ssdp", "ssh",
    }
    if inferred_role in {SERVER, DOMAIN_CONTROLLER}:
        expected_protocols.update({"msrpc", "kerberos", "ldap", "ldaps", "smb"})
    return "unknown" in protocols or bool(protocols - expected_protocols)


def _has_persistent_tls(state: Dict) -> bool:
    for flow in state["flows"]:
        if flow.application_protocol not in {"https", "http2"}:
            continue
        if flow.direction not in {"outbound", "inbound", "external"}:
            continue
        if getattr(flow, "raw_duration_seconds", 0.0) >= 300 or getattr(flow, "beacon_score", 0.0):
            return True
    return False


def _external_smb_observed(state: Dict) -> bool:
    for flow in state["flows"]:
        if flow.application_protocol != "smb":
            continue
        if flow.direction in {"outbound", "inbound", "external"}:
            return True
    return False


def _relationship_concentration(state: Dict) -> float:
    peer_flow_counts = [len(flows) for flows in state["peer_flows"].values()]
    if not peer_flow_counts:
        return 0.0
    return max(peer_flow_counts) / sum(peer_flow_counts)


def _severity(score: float, confidence: float) -> str:
    adjusted_score = score * confidence
    if adjusted_score >= 48:
        return "high"
    if adjusted_score >= 26:
        return "medium"
    if score > 0:
        return "low"
    return "informational"
