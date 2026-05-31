from __future__ import annotations

import ipaddress
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from .registry import HypothesisRegistry
from .schemas import AttackHypothesis, BehavioralDelta
from behavior.role_manager import DOMAIN_CONTROLLER, INFRASTRUCTURE, normalize_role


def _normalize_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_hypothesis_id(hypothesis_type: str, seed: str) -> str:
    return f"{hypothesis_type}:{seed}:{datetime.now(timezone.utc).timestamp()}"


def _score_from_weights(weights: Dict[str, float], values: Dict[str, float]) -> float:
    total = 0.0
    weight_sum = sum(weights.values())
    if weight_sum == 0:
        return 0.0
    for signal, weight in weights.items():
        total += values.get(signal, 0.0) * weight
    return round(total / weight_sum * 100.0, 2)


def deduplicate_evidence(evidence_items: Iterable[str]) -> List[str]:
    seen = set()
    deduplicated = []
    for evidence_item in evidence_items:
        cleaned_item = str(evidence_item).strip()
        if not cleaned_item:
            continue
        evidence_key = cleaned_item.casefold()
        if evidence_key in seen:
            continue
        seen.add(evidence_key)
        deduplicated.append(cleaned_item)
    return deduplicated


COMMON_CLOUD_SERVICE_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in (
        "13.64.0.0/11",
        "20.0.0.0/8",
        "40.64.0.0/10",
        "52.224.0.0/11",
        "104.208.0.0/13",
        "150.171.0.0/16",
    )
)


def _is_internal_ip(ip_address: str) -> bool:
    try:
        return ipaddress.ip_address(ip_address).is_private
    except ValueError:
        return False


def _external_destination_pair(metrics: Dict[str, Any]) -> tuple[str | None, str | None]:
    source = metrics.get("source")
    target = metrics.get("target")
    if not source or not target:
        return None, None
    if _is_internal_ip(source) and not _is_internal_ip(target):
        return source, target
    if _is_internal_ip(target) and not _is_internal_ip(source):
        return target, source
    return source, target


def _is_common_cloud_service(destination: str) -> bool:
    try:
        destination_ip = ipaddress.ip_address(destination)
    except ValueError:
        return False
    return any(destination_ip in network for network in COMMON_CLOUD_SERVICE_NETWORKS)


def _consumer_counts_by_destination(relationship_deltas: Iterable[BehavioralDelta]) -> Dict[str, set[str]]:
    consumers_by_destination: Dict[str, set[str]] = {}
    for delta in relationship_deltas:
        consumer, destination = _external_destination_pair(delta.metrics)
        if not consumer or not destination or consumer == destination:
            continue
        consumers_by_destination.setdefault(destination, set()).add(consumer)
    return consumers_by_destination


def compute_destination_rarity(consumer_count: int) -> float:
    if consumer_count <= 0:
        return 0.0
    return round(1.0 / consumer_count, 4)


def compute_destination_exclusivity(consumer_count: int) -> float:
    if consumer_count <= 0:
        return 0.0
    if consumer_count == 1:
        return 1.0
    return round(max(0.0, 1.0 - ((consumer_count - 1) / 12.0)), 4)


def _confidence_explanation(
    confidence: float,
    positive_factors: List[str],
    contradictory_evidence: List[str],
) -> str:
    positives = ", ".join(f"+ {factor}" for factor in positive_factors)
    negatives = ", ".join(f"- {factor}" for factor in contradictory_evidence) or "- none observed"
    return f"Confidence {confidence:.1f}%. Positive: {positives}. Negative: {negatives}."


def _finding_tier(confidence: float) -> str:
    if confidence >= 85.0:
        return "PRIMARY"
    if confidence >= 70.0:
        return "SECONDARY"
    return "SUPPORTING"


def evaluate_port_scan(
    hypothesis_registry: HypothesisRegistry,
    host_deltas: Iterable[BehavioralDelta],
    host_profiles_by_ip: Dict[str, Any] | None = None,
) -> List[AttackHypothesis]:
    definition = hypothesis_registry.get("port_scan")
    if not definition:
        return []

    results: List[AttackHypothesis] = []
    for delta in host_deltas:
        if delta.entity_type != "host":
            continue
        if delta.delta_type not in {"host_behavior_change", "risk_increase", "risk_decrease"}:
            continue

        metrics = delta.metrics
        new_relationship_count = metrics.get("new_relationship_count", 0)
        unique_ports_delta = metrics.get("unique_ports_delta", 0)
        low_persistence = 1.0 if metrics.get("low_persistence_ratio", 0.0) >= 0.75 else 0.0

        if new_relationship_count >= 5 and unique_ports_delta >= 4:
            confidence = _score_from_weights(definition.confidence_weights, {
                "new_relationship_count": min(new_relationship_count / 10.0, 1.0),
                "unique_ports_delta": min(unique_ports_delta / 10.0, 1.0),
                "low_persistence": low_persistence,
                "risk_delta": min(abs(metrics.get("risk_score_delta", 0)) / 30.0, 1.0),
            })
            results.append(AttackHypothesis(
                hypothesis_id=_build_hypothesis_id(definition.hypothesis_type, delta.delta_id),
                hypothesis_type=definition.hypothesis_type,
                title=definition.title,
                summary=f"Host {delta.entity_id} exhibits port scan indicators based on newly observed relationships and port expansion.",
                impacted_entities=[delta.entity_id],
                supporting_delta_ids=[delta.delta_id],
                supporting_evidence=deduplicate_evidence([f"new_relationships={new_relationship_count}", f"ports_added={unique_ports_delta}"]),
                confidence_explanation=f"Port scan confidence based on {new_relationship_count} new relationships and {unique_ports_delta} new ports.",
                confidence=confidence,
                severity=definition.severity,
                finding_tier=_finding_tier(confidence),
                created_at=_normalize_timestamp(),
                status="new",
                metadata={"signals": definition.signals},
            ))
    return results


def evaluate_host_sweep(
    hypothesis_registry: HypothesisRegistry,
    host_deltas: Iterable[BehavioralDelta],
    host_profiles_by_ip: Dict[str, Any] | None = None,
) -> List[AttackHypothesis]:
    definition = hypothesis_registry.get("host_sweep")
    if not definition:
        return []

    results: List[AttackHypothesis] = []
    for delta in host_deltas:
        if delta.entity_type != "host":
            continue
        if delta.delta_type not in {"host_behavior_change", "risk_increase", "risk_decrease"}:
            continue

        metrics = delta.metrics
        new_peer_count = metrics.get("new_peer_count", metrics.get("new_relationship_count", 0))
        external_host_delta = metrics.get("external_host_delta", 0)
        steady_port_pattern = 1.0 if metrics.get("same_port_peer_count", 0) >= 0.75 else 0.0

        if new_peer_count >= 4 and external_host_delta >= 2:
            confidence = _score_from_weights(definition.confidence_weights, {
                "new_peer_count": min(new_peer_count / 10.0, 1.0),
                "external_host_delta": min(external_host_delta / 5.0, 1.0),
                "steady_port_pattern": steady_port_pattern,
                "risk_delta": min(abs(metrics.get("risk_score_delta", 0)) / 30.0, 1.0),
            })
            results.append(AttackHypothesis(
                hypothesis_id=_build_hypothesis_id(definition.hypothesis_type, delta.delta_id),
                hypothesis_type=definition.hypothesis_type,
                title=definition.title,
                summary=f"Host {delta.entity_id} exhibits host sweep indicators with many new peer relationships.",
                impacted_entities=[delta.entity_id],
                supporting_delta_ids=[delta.delta_id],
                supporting_evidence=deduplicate_evidence([f"new_peers={new_peer_count}", f"external_hosts={external_host_delta}"]),
                confidence_explanation=f"Host sweep confidence based on {new_peer_count} new peer connections across {external_host_delta} external hosts.",
                confidence=confidence,
                severity=definition.severity,
                finding_tier=_finding_tier(confidence),
                created_at=_normalize_timestamp(),
                status="new",
                metadata={"signals": definition.signals},
            ))
    return results


def evaluate_beaconing(
    hypothesis_registry: HypothesisRegistry,
    relationship_deltas: Iterable[BehavioralDelta],
    host_profiles_by_ip: Dict[str, Any] | None = None,
) -> List[AttackHypothesis]:
    """
    Hardened beaconing detection with:
    - 3+ signal requirement (periodicity, persistence, external communication)
    - Contradictory evidence scoring
    - Infrastructure suppression
    - Confidence-based severity mapping
    - Evidence chain documentation
    """
    definition = hypothesis_registry.get("beaconing")
    if not definition:
        return []

    relationship_deltas = list(relationship_deltas)
    host_profiles_by_ip = host_profiles_by_ip or {}
    consumers_by_destination = _consumer_counts_by_destination(relationship_deltas)
    results: List[AttackHypothesis] = []

    for delta in relationship_deltas:
        if delta.delta_type not in {"persistence_increase", "external_relationship_emergence"}:
            continue

        metrics = delta.metrics
        protocols = set(metrics.get("protocols", []))
        if "https" not in protocols and "tls" not in protocols:
            continue

        source = metrics.get("source", "unknown")
        target = metrics.get("target", "unknown")
        consumer, destination = _external_destination_pair(metrics)
        persistence = metrics.get("persistence", 0.0)

        # === SIGNAL COLLECTION ===
        signals = []
        signal_values = {}

        if persistence >= 0.55:
            signals.append("periodicity")
            signal_values["periodicity"] = min(persistence / 1.0, 1.0)

        if persistence >= 0.45:
            signals.append("persistence")
            signal_values["persistence"] = min(persistence / 1.0, 1.0)

        if delta.delta_type == "external_relationship_emergence":
            signals.append("external_relationship")
            signal_values["external_relationship"] = 1.0

        if persistence >= 0.70:
            signals.append("low_jitter")
            signal_values["low_jitter"] = 0.8

        if metrics.get("flows", 1) <= 5:
            signals.append("low_volume")
            signal_values["low_volume"] = 0.6

        consumer_count = len(consumers_by_destination.get(destination, set())) if destination else 0
        destination_rarity = compute_destination_rarity(consumer_count)
        destination_exclusivity = compute_destination_exclusivity(consumer_count)

        if destination_rarity >= 0.5:
            signals.append("rare_destination")
            signal_values["destination_rarity"] = destination_rarity

        if destination_exclusivity >= 0.75:
            signals.append("exclusive_destination")
            signal_values["destination_exclusivity"] = destination_exclusivity

        # === MULTI-SIGNAL REQUIREMENT ===
        required_signals = {"periodicity", "persistence", "external_relationship"}
        has_required = required_signals.intersection(set(signals))
        if len(has_required) < 3:
            continue

        # === CONTRADICTORY EVIDENCE ===
        contradictory_evidence = []
        contradictory_score = 0.0

        target_profile = host_profiles_by_ip.get(target)
        if target_profile:
            role = normalize_role(getattr(target_profile, "role", getattr(target_profile, "inferred_role", "UNKNOWN")))
            infrastructure_roles = {INFRASTRUCTURE, DOMAIN_CONTROLLER}
            if role in infrastructure_roles:
                contradictory_evidence.append("infrastructure_role")
                contradictory_score += 0.25

        if consumer_count >= 2:
            contradictory_evidence.append("shared_destination")
            contradictory_score += min(0.20, consumer_count * 0.015)
        if consumer_count >= 8:
            contradictory_evidence.append("many_internal_consumers")
            contradictory_score += 0.15
        if consumer_count >= 20:
            contradictory_evidence.append("high_destination_fan_in")
            contradictory_score += 0.15
        if destination and _is_common_cloud_service(destination):
            contradictory_evidence.append("common_cloud_service")
            contradictory_score += 0.18

        # === CONFIDENCE CALCULATION ===
        evidence_confidence = _score_from_weights(definition.confidence_weights, signal_values) / 100.0
        destination_confidence = (destination_rarity * 0.14) + (destination_exclusivity * 0.16)
        confidence = min(0.92, evidence_confidence + destination_confidence) - contradictory_score

        if confidence < 0.60:
            continue

        # === SEVERITY MAPPING ===
        if confidence >= 0.95:
            severity = "critical"
        elif confidence >= 0.85:
            severity = "high"
        elif confidence >= 0.75:
            severity = "medium"
        else:
            severity = "low"

        # === EVIDENCE CHAIN ===
        supporting_evidence = deduplicate_evidence(signals)
        contradictory_evidence = deduplicate_evidence(contradictory_evidence)
        confidence_percent = round(confidence * 100, 1)
        positive_factors = sorted(supporting_evidence)
        confidence_explanation = _confidence_explanation(confidence_percent, positive_factors, contradictory_evidence)

        results.append(AttackHypothesis(
            hypothesis_id=_build_hypothesis_id(definition.hypothesis_type, delta.delta_id),
            hypothesis_type=definition.hypothesis_type,
            title=definition.title,
            summary=f"TLS beaconing: {source} <-> {target}",
            impacted_entities=[source, target],
            supporting_delta_ids=[delta.delta_id],
            supporting_evidence=supporting_evidence,
            contradictory_evidence=contradictory_evidence,
            confidence_explanation=confidence_explanation,
            confidence=confidence_percent,
            severity=severity,
            finding_tier=_finding_tier(confidence_percent),
            created_at=_normalize_timestamp(),
            status="new",
            metadata={
                "signals": sorted(signals),
                "relationship_consumer": consumer,
                "relationship_destination": destination,
                "destination_consumer_count": consumer_count,
                "destination_rarity_score": destination_rarity,
                "destination_exclusivity_score": destination_exclusivity,
            },
        ))

    return results


def evaluate_persistent_tls(
    hypothesis_registry: HypothesisRegistry,
    relationship_deltas: Iterable[BehavioralDelta],
    host_profiles_by_ip: Dict[str, Any] | None = None,
) -> List[AttackHypothesis]:
    definition = hypothesis_registry.get("persistent_tls")
    if not definition:
        return []

    results: List[AttackHypothesis] = []
    for delta in relationship_deltas:
        if delta.delta_type != "persistence_increase":
            continue

        metrics = delta.metrics
        protocols = set(metrics.get("protocols", []))
        if "https" not in protocols and "tls" not in protocols:
            continue

        consumer, destination = _external_destination_pair(metrics)
        is_external_tls = bool(consumer and destination and consumer != destination)
        confidence = _score_from_weights(definition.confidence_weights, {
            "https_persistence": min(metrics.get("persistence", 0.0) / 1.0, 1.0),
            "external_tls": 1.0 if is_external_tls else 0.5,
            "risk_delta": 0.0,
        })
        results.append(AttackHypothesis(
            hypothesis_id=_build_hypothesis_id(definition.hypothesis_type, delta.delta_id),
            hypothesis_type=definition.hypothesis_type,
            title=definition.title,
            summary=f"Relationship {delta.metrics.get('source')}->{delta.metrics.get('target')} shows persistent TLS behavior.",
            impacted_entities=[delta.metrics.get("source", "unknown"), delta.metrics.get("target", "unknown")],
            supporting_delta_ids=[delta.delta_id],
            supporting_evidence=deduplicate_evidence([f"https_persistence={metrics.get('persistence', 0.0):.1%}"]),
            confidence_explanation=f"Persistent TLS confidence based on {metrics.get('persistence', 0.0):.1%} persistence ratio.",
            confidence=confidence,
            severity=definition.severity,
            finding_tier=_finding_tier(confidence),
            created_at=_normalize_timestamp(),
            status="new",
            metadata={
                "signals": definition.signals,
                "relationship_consumer": consumer,
                "relationship_destination": destination,
            },
        ))
    return results
