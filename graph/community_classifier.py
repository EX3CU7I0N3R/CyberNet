from __future__ import annotations

import ipaddress
from typing import Dict, Iterable, Tuple

from behavior.role_manager import (
    DOMAIN_CONTROLLER,
    EXTERNAL_SERVICE,
    INFRASTRUCTURE,
    SERVER,
    WORKSTATION,
    normalize_role,
)


ROLE_COMMUNITIES = {
    DOMAIN_CONTROLLER: "Domain Controllers",
    INFRASTRUCTURE: "Infrastructure",
    SERVER: "Servers",
    WORKSTATION: "Workstations",
    EXTERNAL_SERVICE: "External Services",
}


def classify_community(role: str) -> Tuple[str, float]:
    normalized_role = normalize_role(role)
    community = ROLE_COMMUNITIES.get(normalized_role, "Unknown")
    confidence = 0.85 if community != "Unknown" else 0.35
    return community, confidence


def classify_communities(host_profiles: Iterable, relationships: Iterable | None = None, graph_state=None) -> Dict[str, list[str]]:
    communities = {
        "Domain Controllers": [],
        "Infrastructure": [],
        "Servers": [],
        "Workstations": [],
        "External Services": [],
        "Unknown": [],
    }

    for profile in host_profiles:
        role = getattr(profile, "role", getattr(profile, "inferred_role", "UNKNOWN"))
        if normalize_role(role) == "UNKNOWN" and _is_external_ip(getattr(profile, "ip_address", "")):
            role = EXTERNAL_SERVICE
        community, _ = classify_community(role)
        communities[community].append(getattr(profile, "ip_address", getattr(profile, "ip", "")))

    return {name: hosts for name, hosts in communities.items() if hosts}


def classify_graph_nodes(nodes: Iterable, edges: Iterable | None = None) -> Dict[str, list[str]]:
    communities = {
        "Domain Controllers": [],
        "Infrastructure": [],
        "Servers": [],
        "Workstations": [],
        "External Services": [],
        "Unknown": [],
    }

    for node in nodes:
        role = getattr(node, "role", getattr(node, "inferred_role", "UNKNOWN"))
        if normalize_role(role) == "UNKNOWN" and _is_external_ip(node.ip_address):
            role = EXTERNAL_SERVICE
        community, confidence = classify_community(role)
        node.metadata["community_type"] = community
        node.metadata["community_confidence"] = confidence
        communities[community].append(node.ip_address)

    return {name: hosts for name, hosts in communities.items() if hosts}


def _is_external_ip(host_ip: str) -> bool:
    try:
        return not ipaddress.ip_address(host_ip).is_private
    except ValueError:
        return False
