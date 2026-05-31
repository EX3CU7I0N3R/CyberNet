from __future__ import annotations

import ipaddress
from typing import Any, Dict


DOMAIN_CONTROLLER = "DOMAIN_CONTROLLER"
INFRASTRUCTURE = "INFRASTRUCTURE"
SERVER = "SERVER"
WORKSTATION = "WORKSTATION"
EXTERNAL_SERVICE = "EXTERNAL_SERVICE"
UNKNOWN = "UNKNOWN"

INFRASTRUCTURE_PROTOCOLS = {"arp", "dhcp", "dns", "llmnr", "mdns", "nbns", "ntp", "ssdp"}
DOMAIN_CONTROLLER_PROTOCOLS = {"dns", "kerberos", "ldap", "ldaps", "smb", "msrpc"}
SERVER_PORTS = {53, 80, 88, 135, 139, 389, 443, 445, 464, 636, 3389}


def infer_host_role(metrics: Dict[str, Any], state: Dict[str, Any] | None = None, host_ip: str | None = None) -> Dict[str, Any]:
    state = state or {}
    protocols = {str(protocol).lower() for protocol in metrics.get("protocols", [])}
    service_ports = set(state.get("service_ports", set()))
    supporting_signals = []

    if host_ip and _is_external_ip(host_ip):
        supporting_signals.append("external_ip")
        if (
            metrics.get("internal_unique_hosts", 0) >= 2
            or metrics.get("persistent_relationships", 0) >= 2
            or metrics.get("suspicious_flow_count", 0)
            or metrics.get("beacon_flow_count", 0)
        ):
            supporting_signals.append("external_service_behavior")
            return _role(EXTERNAL_SERVICE, 0.82, supporting_signals)
        return _role(UNKNOWN, 0.35, ["external_low_signal_endpoint"])

    inbound_ratio = float(metrics.get("inbound_ratio", 0.0))
    outbound_ratio = float(metrics.get("outbound_ratio", 0.0))
    responded_count = int(metrics.get("responded_flow_count", 0))
    unique_destinations = int(metrics.get("unique_destinations", 0))
    dns_https_heavy = bool(protocols & {"dns", "https", "http"})

    dc_signal_count = len(protocols & DOMAIN_CONTROLLER_PROTOCOLS)
    if (
        {"ldap", "kerberos", "smb"} <= protocols
        or (dc_signal_count >= 4 and inbound_ratio >= 0.35 and responded_count >= 10)
    ):
        supporting_signals.extend(sorted(protocols & DOMAIN_CONTROLLER_PROTOCOLS))
        return _role(DOMAIN_CONTROLLER, 0.84, supporting_signals)

    if unique_destinations >= 20 and int(metrics.get("external_unique_hosts", 0)) >= 20 and dns_https_heavy:
        supporting_signals.extend(["external_destination_fanout", "dns_https_client_behavior"])
        return _role(WORKSTATION, 0.84, supporting_signals)

    if outbound_ratio >= 0.40 and unique_destinations >= 3 and dns_https_heavy:
        supporting_signals.extend(["outbound_dominant", "dns_https_client_behavior", "destination_fanout"])
        return _role(WORKSTATION, 0.84, supporting_signals)

    if outbound_ratio >= 0.35 and unique_destinations >= 2:
        supporting_signals.extend(["outbound_dominant", "client_fanout"])
        return _role(WORKSTATION, 0.70, supporting_signals)

    infrastructure_overlap = protocols & INFRASTRUCTURE_PROTOCOLS
    if "dhcp" in protocols or ({"dns", "ldap"} & protocols and len(infrastructure_overlap) >= 2):
        supporting_signals.extend(sorted(infrastructure_overlap))
        return _role(INFRASTRUCTURE, 0.78, supporting_signals)

    server_port_overlap = len(service_ports & SERVER_PORTS)
    if inbound_ratio >= 0.35 and responded_count >= 10 and server_port_overlap >= 2:
        supporting_signals.extend(["high_inbound_ratio", "stable_service_ports", "many_clients"])
        return _role(SERVER, 0.76, supporting_signals)

    if protocols and protocols.issubset(INFRASTRUCTURE_PROTOCOLS):
        supporting_signals.append("infrastructure_protocol_only")
        return _role(INFRASTRUCTURE, 0.72, supporting_signals)

    return _role(UNKNOWN, 0.35, ["insufficient_role_evidence"])


def normalize_role(role: str | None) -> str:
    normalized = str(role or UNKNOWN).upper()
    aliases = {
        "DOMAIN_CONTROLLER": DOMAIN_CONTROLLER,
        "DOMAIN CONTROLLER": DOMAIN_CONTROLLER,
        "INFRASTRUCTURE_DEVICE": INFRASTRUCTURE,
        "MULTICAST_SERVICE_HOST": INFRASTRUCTURE,
        "INFRASTRUCTURE": INFRASTRUCTURE,
        "SERVER": SERVER,
        "WORKSTATION": WORKSTATION,
        "EXTERNAL_HOST": EXTERNAL_SERVICE,
        "EXTERNAL_SERVICE": EXTERNAL_SERVICE,
        "EXTERNAL SERVICE": EXTERNAL_SERVICE,
        "DOMAIN CONTROLLER": DOMAIN_CONTROLLER,
        "UNKNOWN": UNKNOWN,
    }
    return aliases.get(normalized, UNKNOWN)


def role_to_display(role: str | None) -> str:
    return normalize_role(role).replace("_", " ").title()


def _role(role: str, confidence: float, supporting_signals: list[str]) -> Dict[str, Any]:
    return {
        "role": role,
        "confidence": confidence,
        "supporting_signals": supporting_signals,
    }


def _is_external_ip(host_ip: str) -> bool:
    try:
        return not ipaddress.ip_address(host_ip).is_private
    except ValueError:
        return False
