from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from .registry import HypothesisRegistry
from .schemas import AttackHypothesis, BehavioralDelta


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
                supporting_evidence=[f"new_relationships={new_relationship_count}", f"ports_added={unique_ports_delta}"],
                confidence_explanation=f"Port scan confidence based on {new_relationship_count} new relationships and {unique_ports_delta} new ports.",
                confidence=confidence,
                severity=definition.severity,
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
                supporting_evidence=[f"new_peers={new_peer_count}", f"external_hosts={external_host_delta}"],
                confidence_explanation=f"Host sweep confidence based on {new_peer_count} new peer connections across {external_host_delta} external hosts.",
                confidence=confidence,
                severity=definition.severity,
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

    host_profiles_by_ip = host_profiles_by_ip or {}
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
            role = target_profile.inferred_role if hasattr(target_profile, "inferred_role") else "unknown"
            infrastructure_roles = {"infrastructure", "domain_controller", "service_discovery", "update_infrastructure", "dns_server"}
            if role in infrastructure_roles:
                contradictory_evidence.append(f"destination role is '{role}' (infrastructure pattern)")
                contradictory_score += 0.25

        # === CONFIDENCE CALCULATION ===
        confidence = _score_from_weights(definition.confidence_weights, signal_values)
        confidence = confidence / 100.0
        confidence -= contradictory_score

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
        supporting_evidence = [f"signal: {sig}" for sig in signals]
        confidence_explanation = (
            f"Detected {len(signals)} signals ({', '.join(sorted(signals))}). "
            f"Persistence={persistence:.1%}, ExternalPath={delta.delta_type}. "
            f"Base confidence: {confidence:.1%}"
            + (f" - {len(contradictory_evidence)} contradictions applied." if contradictory_evidence else "")
        )

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
            confidence=round(confidence * 100, 1),
            severity=severity,
            created_at=_normalize_timestamp(),
            status="new",
            metadata={"signals": sorted(signals)},
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

        confidence = _score_from_weights(definition.confidence_weights, {
            "https_persistence": min(metrics.get("persistence", 0.0) / 1.0, 1.0),
            "external_tls": 1.0 if delta.delta_type == "external_relationship_emergence" else 0.5,
            "risk_delta": 0.0,
        })
        results.append(AttackHypothesis(
            hypothesis_id=_build_hypothesis_id(definition.hypothesis_type, delta.delta_id),
            hypothesis_type=definition.hypothesis_type,
            title=definition.title,
            summary=f"Relationship {delta.metrics.get('source')}->{delta.metrics.get('target')} shows persistent TLS behavior.",
            impacted_entities=[delta.metrics.get("source", "unknown"), delta.metrics.get("target", "unknown")],
            supporting_delta_ids=[delta.delta_id],
            supporting_evidence=[f"https_persistence={metrics.get('persistence', 0.0):.1%}"],
            confidence_explanation=f"Persistent TLS confidence based on {metrics.get('persistence', 0.0):.1%} persistence ratio.",
            confidence=confidence,
            severity=definition.severity,
            created_at=_normalize_timestamp(),
            status="new",
            metadata={"signals": definition.signals},
        ))
    return results
