from __future__ import annotations

import hashlib
import importlib.util
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .baseline import BehavioralBaselineManager
from .schemas import BehavioralDelta, HostBaselineSummary, RelationshipBaselineSummary


def _load_behavior_schemas() -> Any:
    package_root = Path(__file__).resolve().parents[1]
    schema_path = package_root / "behavior" / "schemas.py"
    spec = importlib.util.spec_from_file_location("behavior_schemas", str(schema_path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_behavior_schemas = _load_behavior_schemas()


def _normalize_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _classify_direction(src_ip: str, dst_ip: str) -> str:
    import ipaddress

    RESERVED_RANGES = {
        "loopback": ipaddress.ip_network("127.0.0.0/8"),
        "link_local": ipaddress.ip_network("169.254.0.0/16"),
        "broadcast": ipaddress.ip_network("255.255.255.255/32"),
        "this_network": ipaddress.ip_network("0.0.0.0/8"),
        "multicast": ipaddress.ip_network("224.0.0.0/4"),
        "reserved": ipaddress.ip_network("240.0.0.0/4"),
    }
    PRIVATE_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    ]

    def classify(ip_str: str) -> str:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return "error"

        for special_type, network in RESERVED_RANGES.items():
            if ip_obj in network:
                return special_type

        for network in PRIVATE_RANGES:
            if ip_obj in network:
                return "internal"

        return "external"

    src_class = classify(src_ip)
    dst_class = classify(dst_ip)

    if src_class == "error" or dst_class == "error":
        return "error"
    if dst_class == "broadcast":
        return "broadcast"
    if dst_class == "multicast":
        return "multicast"
    if src_class == "loopback" or dst_class == "loopback":
        return "loopback"
    if src_class == "internal" and dst_class == "internal":
        return "internal"
    if src_class == "external" and dst_class == "external":
        return "external"
    if src_class == "internal" and dst_class == "external":
        return "outbound"
    if src_class == "external" and dst_class == "internal":
        return "inbound"

    return "unknown"


def _build_delta_id(entity_type: str, entity_id: str, delta_type: str) -> str:
    digest = hashlib.sha256(f"{entity_type}:{entity_id}:{delta_type}:{uuid.uuid4().hex}".encode()).hexdigest()
    return digest[:16]


def detect_host_deltas(
    current_profiles: Iterable[Any],
    previous_profiles: Iterable[Any],
    historical_baseline: Optional[Dict[str, HostBaselineSummary]] = None,
) -> List[BehavioralDelta]:
    current_index = {profile.ip_address: profile for profile in current_profiles}
    previous_index = {profile.ip_address: profile for profile in previous_profiles}
    deltas: List[BehavioralDelta] = []

    for host_id, current in current_index.items():
        if host_id not in previous_index:
            deltas.append(BehavioralDelta(
                delta_id=_build_delta_id("host", host_id, "new_host"),
                entity_type="host",
                delta_type="new_host",
                entity_id=host_id,
                host_id=host_id,
                detected_at=_normalize_timestamp(),
                confidence=0.75,
                severity="informational",
                summary=f"Host {host_id} appears for the first time in the current snapshot.",
                metrics={
                    "current_unique_ports": current.unique_ports,
                    "current_external_unique_hosts": current.external_unique_hosts,
                    "current_protocols": current.protocols,
                },
            ))
            continue

        previous = previous_index[host_id]
        risk_delta = round(current.risk_score - previous.risk_score, 4)
        unique_ports_delta = current.unique_ports - previous.unique_ports
        persistent_delta = round(current.persistent_connection_ratio - previous.persistent_connection_ratio, 4)
        new_relationship_count = current.protocol_relationships - previous.protocol_relationships
        new_peer_count = current.unique_peers - previous.unique_peers
        external_host_delta = current.external_unique_hosts - previous.external_unique_hosts
        low_persistence_ratio = 1.0 if current.persistent_relationships < previous.persistent_relationships else 0.0
        same_port_peer_count = 1.0 if new_peer_count >= 3 and unique_ports_delta <= 2 else 0.0
        protocol_set = set(current.protocols)
        previous_protocol_set = set(previous.protocols)
        new_protocols = sorted(protocol_set - previous_protocol_set)
        removed_protocols = sorted(previous_protocol_set - protocol_set)

        baseline_comparison = None
        if historical_baseline and host_id in historical_baseline:
            baseline = historical_baseline[host_id]
            baseline_comparison = {
                "risk_score_mean": baseline.risk_score_mean,
                "risk_score_std": baseline.risk_score_std,
                "unique_port_mean": baseline.unique_port_mean,
                "average_persistence": baseline.average_persistence,
            }

        if abs(risk_delta) >= 15 or (baseline_comparison and risk_delta >= max(15.0, baseline_comparison["risk_score_mean"] * 0.30)):
            delta_type = "risk_increase" if risk_delta > 0 else "risk_decrease"
            deltas.append(BehavioralDelta(
                delta_id=_build_delta_id("host", host_id, delta_type),
                entity_type="host",
                delta_type=delta_type,
                entity_id=host_id,
                host_id=host_id,
                detected_at=_normalize_timestamp(),
                confidence=0.80,
                severity="medium" if delta_type == "risk_increase" else "low",
                summary=f"Host {host_id} risk score changed by {risk_delta}.",
                metrics={
                    "risk_score_previous": previous.risk_score,
                    "risk_score_current": current.risk_score,
                    "risk_score_delta": risk_delta,
                },
                baseline_comparison=baseline_comparison,
            ))

        if new_protocols or removed_protocols:
            deltas.append(BehavioralDelta(
                delta_id=_build_delta_id("host", host_id, "protocol_change"),
                entity_type="host",
                delta_type="protocol_change",
                entity_id=host_id,
                host_id=host_id,
                detected_at=_normalize_timestamp(),
                confidence=0.70,
                severity="informational",
                summary=f"Host {host_id} has protocol changes: added {new_protocols}, removed {removed_protocols}.",
                metrics={
                    "new_protocols": new_protocols,
                    "removed_protocols": removed_protocols,
                    "previous_protocols": previous.protocols,
                    "current_protocols": current.protocols,
                },
                baseline_comparison=baseline_comparison,
            ))

        if abs(persistent_delta) >= 0.20:
            deltas.append(BehavioralDelta(
                delta_id=_build_delta_id("host", host_id, "persistence_change"),
                entity_type="host",
                delta_type="persistence_change",
                entity_id=host_id,
                host_id=host_id,
                detected_at=_normalize_timestamp(),
                confidence=0.75,
                severity="informational",
                summary=f"Host {host_id} persistence changed by {persistent_delta}.",
                metrics={
                    "persistent_ratio_previous": previous.persistent_connection_ratio,
                    "persistent_ratio_current": current.persistent_connection_ratio,
                    "persistent_ratio_delta": persistent_delta,
                },
                baseline_comparison=baseline_comparison,
            ))

        if new_relationship_count or new_peer_count or external_host_delta or same_port_peer_count or low_persistence_ratio:
            deltas.append(BehavioralDelta(
                delta_id=_build_delta_id("host", host_id, "host_behavior_change"),
                entity_type="host",
                delta_type="host_behavior_change",
                entity_id=host_id,
                host_id=host_id,
                detected_at=_normalize_timestamp(),
                confidence=0.70,
                severity="informational",
                summary=f"Host {host_id} has behavioral profile changes in relationships and persistence.",
                metrics={
                    "new_relationship_count": new_relationship_count,
                    "new_peer_count": new_peer_count,
                    "external_host_delta": external_host_delta,
                    "same_port_peer_count": same_port_peer_count,
                    "low_persistence_ratio": low_persistence_ratio,
                    "unique_ports_delta": unique_ports_delta,
                },
                baseline_comparison=baseline_comparison,
            ))

    for host_id in previous_index.keys() - current_index.keys():
        deltas.append(BehavioralDelta(
            delta_id=_build_delta_id("host", host_id, "removed_host"),
            entity_type="host",
            delta_type="removed_host",
            entity_id=host_id,
            host_id=host_id,
            detected_at=_normalize_timestamp(),
            confidence=0.70,
            severity="informational",
            summary=f"Host {host_id} no longer appears in the current snapshot.",
            metrics={
                "previous_unique_ports": previous_index[host_id].unique_ports,
                "previous_external_unique_hosts": previous_index[host_id].external_unique_hosts,
            },
        ))

    return deltas


def detect_relationship_deltas(
    current_relationships: Iterable[HostRelationship],
    previous_relationships: Iterable[HostRelationship],
    historical_baseline: Optional[Dict[str, RelationshipBaselineSummary]] = None,
) -> List[BehavioralDelta]:
    current_index = {relationship.edge_id: relationship for relationship in current_relationships}
    previous_index = {relationship.edge_id: relationship for relationship in previous_relationships}
    deltas: List[BehavioralDelta] = []

    for edge_id, current in current_index.items():
        if edge_id not in previous_index:
            direction = _classify_direction(current.source, current.target)
            delta_type = "new_relationship"
            summary = f"New relationship {current.source}->{current.target} appears with protocols {current.protocols}."
            if direction in {"inbound", "outbound"}:
                delta_type = "external_relationship_emergence"
                summary = f"External relationship {current.source}->{current.target} emerged with direction {direction}."
            deltas.append(BehavioralDelta(
                delta_id=_build_delta_id("relationship", edge_id, delta_type),
                entity_type="relationship",
                delta_type=delta_type,
                entity_id=edge_id,
                relationship_id=edge_id,
                detected_at=_normalize_timestamp(),
                confidence=0.80,
                severity="informational",
                summary=summary,
                metrics={
                    "source": current.source,
                    "target": current.target,
                    "protocols": current.protocols,
                    "persistence": current.persistence,
                },
                baseline_comparison=(
                    {
                        "persistence_mean": historical_baseline[edge_id].persistence_mean,
                        "average_flow_count": historical_baseline[edge_id].average_flow_count,
                    }
                    if historical_baseline and edge_id in historical_baseline
                    else None
                ),
            ))
            continue

        previous = previous_index[edge_id]
        persistence_delta = round(current.persistence - previous.persistence, 4)
        protocol_set = set(current.protocols)
        previous_protocol_set = set(previous.protocols)
        new_protocols = sorted(protocol_set - previous_protocol_set)
        removed_protocols = sorted(previous_protocol_set - protocol_set)

        baseline_comparison = None
        if historical_baseline and edge_id in historical_baseline:
            baseline = historical_baseline[edge_id]
            baseline_comparison = {
                "persistence_mean": baseline.persistence_mean,
                "persistence_std": baseline.persistence_std,
                "average_flow_count": baseline.average_flow_count,
            }

        if persistence_delta >= 0.20:
            deltas.append(BehavioralDelta(
                delta_id=_build_delta_id("relationship", edge_id, "persistence_increase"),
                entity_type="relationship",
                delta_type="persistence_increase",
                entity_id=edge_id,
                relationship_id=edge_id,
                detected_at=_normalize_timestamp(),
                confidence=0.80,
                severity="medium",
                summary=f"Relationship {current.source}->{current.target} persistence increased by {persistence_delta}.",
                metrics={
                    "persistence_previous": previous.persistence,
                    "persistence_current": current.persistence,
                    "persistence_delta": persistence_delta,
                    "source": current.source,
                    "target": current.target,
                    "protocols": current.protocols,
                    "flows": getattr(current, "flows", 0),
                },
                baseline_comparison=baseline_comparison,
            ))

        if new_protocols or removed_protocols:
            deltas.append(BehavioralDelta(
                delta_id=_build_delta_id("relationship", edge_id, "protocol_evolution"),
                entity_type="relationship",
                delta_type="protocol_evolution",
                entity_id=edge_id,
                relationship_id=edge_id,
                detected_at=_normalize_timestamp(),
                confidence=0.70,
                severity="informational",
                summary=f"Relationship {current.source}->{current.target} protocol set changed: added {new_protocols}, removed {removed_protocols}.",
                metrics={
                    "new_protocols": new_protocols,
                    "removed_protocols": removed_protocols,
                    "previous_protocols": previous.protocols,
                    "current_protocols": current.protocols,
                },
                baseline_comparison=baseline_comparison,
            ))

    for edge_id in previous_index.keys() - current_index.keys():
        previous = previous_index[edge_id]
        deltas.append(BehavioralDelta(
            delta_id=_build_delta_id("relationship", edge_id, "removed_relationship"),
            entity_type="relationship",
            delta_type="removed_relationship",
            entity_id=edge_id,
            relationship_id=edge_id,
            detected_at=_normalize_timestamp(),
            confidence=0.70,
            severity="informational",
            summary=f"Relationship {previous.source}->{previous.target} no longer appears in the current snapshot.",
            metrics={
                "source": previous.source,
                "target": previous.target,
                "protocols": previous.protocols,
            },
        ))

    return deltas
