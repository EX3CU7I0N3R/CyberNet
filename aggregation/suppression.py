from dataclasses import dataclass, field
from typing import Iterable, Optional


@dataclass(frozen=True)
class SuppressionDecision:
    suppressed: bool
    reason: str = ""
    category: str = ""


@dataclass(frozen=True)
class SuppressionPolicy:
    noisy_protocols: frozenset[str] = field(default_factory=lambda: frozenset({
        "arp",
        "dhcp",
        "llmnr",
        "mdns",
        "nbns",
        "ssdp",
    }))
    noisy_udp_ports: frozenset[int] = field(default_factory=lambda: frozenset({
        67,
        68,
        137,
        1900,
        5353,
        5355,
    }))
    suppressed_directions: frozenset[str] = field(default_factory=lambda: frozenset({
        "broadcast",
        "multicast",
        "loopback",
    }))

    @classmethod
    def with_overrides(
        cls,
        noisy_protocols: Optional[Iterable[str]] = None,
        noisy_udp_ports: Optional[Iterable[int]] = None,
        suppressed_directions: Optional[Iterable[str]] = None,
    ) -> "SuppressionPolicy":
        policy = cls()
        return cls(
            noisy_protocols=frozenset(noisy_protocols) if noisy_protocols is not None else policy.noisy_protocols,
            noisy_udp_ports=frozenset(noisy_udp_ports) if noisy_udp_ports is not None else policy.noisy_udp_ports,
            suppressed_directions=(
                frozenset(suppressed_directions)
                if suppressed_directions is not None
                else policy.suppressed_directions
            ),
        )

    def evaluate_flow(self, flow) -> SuppressionDecision:
        protocol = str(flow.application_protocol or "").lower()
        if protocol in self.noisy_protocols:
            return SuppressionDecision(True, f"expected_{protocol}_infrastructure_traffic", "infrastructure")

        if flow.direction in self.suppressed_directions:
            return SuppressionDecision(True, f"expected_{flow.direction}_traffic", "infrastructure")

        if flow.transport_layer == "arp":
            return SuppressionDecision(True, "expected_arp_resolution", "infrastructure")

        if flow.transport_layer == "udp":
            ports = {flow.initiator_port, flow.responder_port}
            noisy_matches = {port for port in ports if port in self.noisy_udp_ports}
            if noisy_matches:
                port_list = ",".join(str(port) for port in sorted(noisy_matches))
                return SuppressionDecision(True, f"expected_udp_service_port_{port_list}", "infrastructure")

        return SuppressionDecision(False)
