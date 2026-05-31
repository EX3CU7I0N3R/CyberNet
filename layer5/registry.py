from __future__ import annotations

from typing import Dict

from .schemas import HypothesisDefinition


HYPOTHESIS_DEFINITIONS: Dict[str, HypothesisDefinition] = {
    "port_scan": HypothesisDefinition(
        hypothesis_type="port_scan",
        title="Port Scan",
        description="Rapid emergence of many low-persistence relationships from a host consistent with port scanning.",
        signals=["new_relationship_count", "unique_ports_delta", "low_persistence"],
        severity="medium",
        confidence_weights={
            "new_relationship_count": 0.45,
            "unique_ports_delta": 0.25,
            "low_persistence": 0.20,
            "risk_delta": 0.10,
        },
    ),
    "host_sweep": HypothesisDefinition(
        hypothesis_type="host_sweep",
        title="Host Sweep",
        description="Repeated connection attempts from one host to many peers on the same or similar ports.",
        signals=["new_peer_count", "external_host_delta", "steady_port_pattern"],
        severity="medium",
        confidence_weights={
            "new_peer_count": 0.40,
            "external_host_delta": 0.25,
            "steady_port_pattern": 0.20,
            "risk_delta": 0.15,
        },
    ),
    "beaconing": HypothesisDefinition(
        hypothesis_type="beaconing",
        title="Beaconing",
        description="Periodic, low-payload external communication with interval stability, consistent with command and control polling.",
        signals=["periodicity", "persistence", "external_relationship"],
        severity="high",
        confidence_weights={
            "periodicity": 0.35,
            "persistence": 0.35,
            "external_relationship": 0.20,
            "risk_delta": 0.10,
        },
    ),
    "persistent_tls": HypothesisDefinition(
        hypothesis_type="persistent_tls",
        title="Persistent TLS",
        description="Long-lived TLS relationships to external destinations supporting potential covert channels.",
        signals=["https_persistence", "external_tls", "session_duration"],
        severity="high",
        confidence_weights={
            "https_persistence": 0.45,
            "external_tls": 0.35,
            "risk_delta": 0.20,
        },
    ),
}


class HypothesisRegistry:
    def __init__(self, definitions: Dict[str, HypothesisDefinition] = None):
        self._definitions = definitions or HYPOTHESIS_DEFINITIONS.copy()

    def get(self, hypothesis_type: str) -> HypothesisDefinition | None:
        return self._definitions.get(hypothesis_type)

    def list(self) -> list[HypothesisDefinition]:
        return list(self._definitions.values())

    def add(self, definition: HypothesisDefinition) -> None:
        self._definitions[definition.hypothesis_type] = definition

    def remove(self, hypothesis_type: str) -> None:
        self._definitions.pop(hypothesis_type, None)
