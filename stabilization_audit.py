from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

from behavior.node_filters import is_non_investigative_node
from behavior.role_manager import normalize_role


def write_stabilization_exports(
    *,
    host_profiles: Iterable,
    graph_state,
    hypotheses: Iterable,
    investigation_candidates: Iterable,
    temporal_snapshots: Iterable,
    output_dir: str = "output",
) -> dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    host_profiles = list(host_profiles)
    hypotheses = list(hypotheses)
    investigation_candidates = list(investigation_candidates)
    temporal_snapshots = list(temporal_snapshots)

    reports = {
        "community_audit": _write_community_audit(output_path, graph_state),
        "graph_consistency": _write_graph_consistency(output_path, graph_state),
        "role_consistency": _write_role_consistency(output_path, host_profiles, graph_state, investigation_candidates),
        "hypothesis_validation": _write_hypothesis_validation(output_path, hypotheses),
        "candidate_validation": _write_candidate_validation(output_path, investigation_candidates),
        "snapshot_quality": _write_snapshot_quality(output_path, temporal_snapshots),
        "layer6_readiness": _write_layer6_readiness(output_path, host_profiles, graph_state, hypotheses, investigation_candidates),
    }
    reports["stable"] = _is_stable(reports)
    return reports


def _write_community_audit(output_path: Path, graph_state) -> dict:
    rows = []
    for node in graph_state.nodes:
        ip_address = node.ip_address
        rows.append({
            "ip": ip_address,
            "role": normalize_role(getattr(node, "role", getattr(node, "inferred_role", "UNKNOWN"))),
            "role_confidence": round(float(node.metadata.get("role_confidence", 0.0)) * 100, 1),
            "community": node.metadata.get("community_type", "Unknown"),
            "is_internal": _is_internal_ip(ip_address),
            "is_external": _is_external_ip(ip_address),
            "risk_score": float(getattr(node, "risk_score", 0.0)),
        })

    csv_path = output_path / "community_audit.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["ip", "role", "role_confidence", "community", "is_internal", "is_external", "risk_score"],
        )
        writer.writeheader()
        writer.writerows(rows)

    return {"path": str(csv_path), "rows": len(rows)}


def _write_graph_consistency(output_path: Path, graph_state) -> dict:
    communities = graph_state.metadata.get("communities", {})
    classified_nodes = sum(len(nodes) for nodes in communities.values())
    suppressed_nodes = sum(1 for node in graph_state.nodes if is_non_investigative_node(node))
    report = {
        "graph_nodes": graph_state.node_count,
        "classified_nodes": classified_nodes,
        "unclassified_nodes": max(graph_state.node_count - classified_nodes, 0),
        "community_count": len(communities),
        "community_distribution": {name: len(nodes) for name, nodes in communities.items()},
        "role_count": dict(Counter(normalize_role(getattr(node, "role", getattr(node, "inferred_role", "UNKNOWN"))) for node in graph_state.nodes)),
        "investigative_nodes": graph_state.node_count - suppressed_nodes,
        "suppressed_nodes": suppressed_nodes,
        "valid": graph_state.node_count == classified_nodes and graph_state.node_count - classified_nodes == 0,
    }
    _write_json(output_path / "graph_consistency.json", report)
    return report


def _write_role_consistency(output_path: Path, host_profiles: list, graph_state, investigation_candidates: list) -> dict:
    profiles_by_ip = {profile.ip_address: normalize_role(getattr(profile, "role", getattr(profile, "inferred_role", "UNKNOWN"))) for profile in host_profiles}
    graph_roles_by_ip = {node.ip_address: normalize_role(getattr(node, "role", getattr(node, "inferred_role", "UNKNOWN"))) for node in graph_state.nodes}
    candidate_roles_by_ip = {candidate.host: normalize_role(getattr(candidate, "host_role", "UNKNOWN")) for candidate in investigation_candidates}

    mismatches = []
    for host, profile_role in sorted(profiles_by_ip.items()):
        graph_role = graph_roles_by_ip.get(host)
        if graph_role != profile_role:
            mismatches.append({
                "host": host,
                "host_profile_role": profile_role,
                "graph_node_role": graph_role,
                "investigation_candidate_role": candidate_roles_by_ip.get(host),
            })

    for host, candidate_role in sorted(candidate_roles_by_ip.items()):
        profile_role = profiles_by_ip.get(host)
        graph_role = graph_roles_by_ip.get(host)
        if candidate_role != profile_role or candidate_role != graph_role:
            mismatch = {
                "host": host,
                "host_profile_role": profile_role,
                "graph_node_role": graph_role,
                "investigation_candidate_role": candidate_role,
            }
            if mismatch not in mismatches:
                mismatches.append(mismatch)

    report = {
        "checked_hosts": len(profiles_by_ip),
        "candidate_hosts": len(candidate_roles_by_ip),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "valid": len(mismatches) == 0,
    }
    _write_json(output_path / "role_consistency_report.json", report)
    return report


def _write_hypothesis_validation(output_path: Path, hypotheses: list) -> dict:
    errors = []
    for hypothesis in hypotheses:
        missing_fields = []
        if not hypothesis.supporting_evidence:
            missing_fields.append("supporting_evidence")
        if hypothesis.contradictory_evidence is None:
            missing_fields.append("contradictory_evidence")
        if hypothesis.confidence is None:
            missing_fields.append("confidence")
        if not hypothesis.confidence_explanation:
            missing_fields.append("confidence_explanation")
        if missing_fields:
            errors.append({
                "hypothesis_id": hypothesis.hypothesis_id,
                "missing_fields": missing_fields,
            })

    report = {
        "hypotheses_checked": len(hypotheses),
        "error_count": len(errors),
        "errors": errors,
        "valid": len(errors) == 0,
    }
    _write_json(output_path / "hypothesis_validation.json", report)
    return report


def _write_candidate_validation(output_path: Path, investigation_candidates: list) -> dict:
    errors = []
    for candidate in investigation_candidates:
        missing_fields = []
        if not candidate.host:
            missing_fields.append("host")
        if not candidate.priority:
            missing_fields.append("priority")
        if candidate.priority_score is None:
            missing_fields.append("priority_score")
        if not candidate.host_role:
            missing_fields.append("host_role")
        if candidate.risk is None:
            missing_fields.append("risk")
        if not candidate.findings:
            missing_fields.append("findings")
        if not candidate.priority_explanation:
            missing_fields.append("priority_explanation")
        if missing_fields:
            errors.append({
                "host": candidate.host,
                "missing_fields": missing_fields,
            })

    report = {
        "candidates_checked": len(investigation_candidates),
        "error_count": len(errors),
        "errors": errors,
        "valid": len(errors) == 0,
    }
    _write_json(output_path / "investigation_candidate_validation.json", report)
    return report


def _write_snapshot_quality(output_path: Path, temporal_snapshots: list) -> dict:
    quality_reasons = Counter(snapshot.metadata.get("quality_reason", "unknown") for snapshot in temporal_snapshots)
    quality_scores = [float(snapshot.metadata.get("quality_score", 0.0)) for snapshot in temporal_snapshots]
    quality_score = round(sum(quality_scores) / len(quality_scores), 4) if quality_scores else 0.0
    report = {
        "total_snapshots": len(temporal_snapshots),
        "meaningful_snapshots": quality_reasons.get("useful_snapshot", 0),
        "redundant_snapshots": quality_reasons.get("redundant_snapshot", 0),
        "quality_score": quality_score,
        "valid": quality_score >= 0.90,
    }
    _write_json(output_path / "snapshot_quality.json", report)
    return report


def _write_layer6_readiness(output_path: Path, host_profiles: list, graph_state, hypotheses: list, investigation_candidates: list) -> dict:
    missing_components = []
    if not host_profiles:
        missing_components.append("HostProfile")
    if not hypotheses:
        missing_components.append("AttackHypothesis")
    if not all(hypothesis.supporting_evidence is not None and hypothesis.contradictory_evidence is not None for hypothesis in hypotheses):
        missing_components.append("EvidenceChain")
    if not investigation_candidates:
        missing_components.append("InvestigationCandidate")
    if graph_state is None or not graph_state.nodes:
        missing_components.append("GraphContext")

    report = {
        "ready": not missing_components,
        "missing_components": missing_components,
    }
    _write_json(output_path / "layer6_readiness.json", report)
    return report


def _is_stable(reports: dict) -> bool:
    return (
        reports["graph_consistency"]["valid"]
        and reports["role_consistency"]["valid"]
        and reports["hypothesis_validation"]["valid"]
        and reports["candidate_validation"]["valid"]
        and reports["snapshot_quality"]["valid"]
        and reports["layer6_readiness"]["ready"]
    )


def _write_json(path: Path, report: dict) -> None:
    with path.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")


def _is_internal_ip(ip_address: str) -> bool:
    try:
        import ipaddress

        return ipaddress.ip_address(ip_address).is_private
    except ValueError:
        return False


def _is_external_ip(ip_address: str) -> bool:
    try:
        import ipaddress

        return not ipaddress.ip_address(ip_address).is_private
    except ValueError:
        return False
