from __future__ import annotations

import importlib.util
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List

from .schemas import HostBaselineSummary, RelationshipBaselineSummary


def _load_behavior_schemas() -> Any:
    package_root = Path(__file__).resolve().parents[1]
    schema_path = package_root / "behavior" / "schemas.py"
    spec = importlib.util.spec_from_file_location("behavior_schemas", str(schema_path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_behavior_schemas = _load_behavior_schemas()


class BehavioralBaselineManager:
    def build_immediate_host_baseline(self, current_profiles: Iterable[Any], previous_profiles: Iterable[Any]) -> Dict[str, dict]:
        current = {profile.ip_address: profile for profile in current_profiles}
        previous = {profile.ip_address: profile for profile in previous_profiles}
        return {
            "hosts": {
                ip: {
                    "current": self._summarize_host(profile),
                    "previous": self._summarize_host(previous[ip]) if ip in previous else None,
                }
                for ip, profile in current.items()
            }
        }

    def build_immediate_relationship_baseline(self, current_relationships: Iterable[Any], previous_relationships: Iterable[Any]) -> Dict[str, dict]:
        current = {relationship.edge_id: relationship for relationship in current_relationships}
        previous = {relationship.edge_id: relationship for relationship in previous_relationships}
        return {
            "relationships": {
                edge_id: {
                    "current": self._summarize_relationship(relationship),
                    "previous": self._summarize_relationship(previous[edge_id]) if edge_id in previous else None,
                }
                for edge_id, relationship in current.items()
            }
        }

    def build_historical_host_baseline(self, snapshots: Iterable[Iterable[HostProfile]]) -> Dict[str, HostBaselineSummary]:
        samples: Dict[str, dict] = defaultdict(lambda: {
            "risk_scores": [],
            "persistences": [],
            "unique_ports": [],
            "protocol_counts": defaultdict(int),
        })
        for snapshot in snapshots:
            for profile in snapshot:
                state = samples[profile.ip_address]
                state["risk_scores"].append(profile.risk_score)
                state["persistences"].append(profile.persistent_connection_ratio)
                state["unique_ports"].append(profile.unique_ports)
                for protocol in profile.protocols:
                    state["protocol_counts"][protocol] += 1

        baseline: Dict[str, HostBaselineSummary] = {}
        for host_id, state in samples.items():
            baseline[host_id] = HostBaselineSummary(
                host_id=host_id,
                risk_score_mean=mean(state["risk_scores"]) if state["risk_scores"] else 0.0,
                risk_score_std=pstdev(state["risk_scores"]) if len(state["risk_scores"]) > 1 else 0.0,
                observed_protocols=dict(state["protocol_counts"]),
                average_persistence=mean(state["persistences"]) if state["persistences"] else 0.0,
                unique_port_mean=mean(state["unique_ports"]) if state["unique_ports"] else 0.0,
                sample_count=len(state["risk_scores"]),
            )
        return baseline

    def build_historical_relationship_baseline(self, snapshots: Iterable[Iterable[HostRelationship]]) -> Dict[str, RelationshipBaselineSummary]:
        samples: Dict[str, dict] = defaultdict(lambda: {
            "persistences": [],
            "flow_counts": [],
            "protocol_counts": defaultdict(int),
        })
        for snapshot in snapshots:
            for relationship in snapshot:
                state = samples[relationship.edge_id]
                state["persistences"].append(relationship.persistence)
                state["flow_counts"].append(relationship.flows)
                for protocol in relationship.protocols:
                    state["protocol_counts"][protocol] += 1

        baseline: Dict[str, RelationshipBaselineSummary] = {}
        for relationship_id, state in samples.items():
            baseline[relationship_id] = RelationshipBaselineSummary(
                relationship_id=relationship_id,
                persistence_mean=mean(state["persistences"]) if state["persistences"] else 0.0,
                persistence_std=pstdev(state["persistences"]) if len(state["persistences"]) > 1 else 0.0,
                observed_protocols=dict(state["protocol_counts"]),
                average_flow_count=mean(state["flow_counts"]) if state["flow_counts"] else 0.0,
                sample_count=len(state["persistences"]),
            )
        return baseline

    @staticmethod
    def _summarize_host(profile: HostProfile) -> dict:
        return {
            "risk_score": profile.risk_score,
            "protocols": profile.protocols,
            "persistent_relationships": profile.persistent_relationships,
            "unique_ports": profile.unique_ports,
            "external_unique_hosts": profile.external_unique_hosts,
            "persistent_connection_ratio": profile.persistent_connection_ratio,
            "behavioral_indicators": profile.behavioral_indicators,
            "inferred_role": profile.inferred_role,
            "role": getattr(profile, "role", profile.inferred_role),
        }

    @staticmethod
    def _summarize_relationship(relationship: HostRelationship) -> dict:
        return {
            "persistence": relationship.persistence,
            "protocols": relationship.protocols,
            "relationship_risk": relationship.relationship_risk,
            "flows": relationship.flows,
            "total_bytes": relationship.total_bytes,
            "relationship_indicators": relationship.relationship_indicators,
        }
