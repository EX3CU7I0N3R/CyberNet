"""
Layer 4: Graph Builder
Converts host profiles and relationships into graph-native node and edge entities.
"""

from hashlib import sha256
from typing import Dict, List, Optional

from behavior.schemas import GraphEdge, GraphNode, HostProfile, HostRelationship


def build_graph_nodes(host_profiles: List[HostProfile]) -> List[GraphNode]:
    """
    Convert host profiles into graph-native node entities.
    
    Each node includes:
    - Identity (node_id, ip_address, hostname, inferred_role)
    - Behavior (risk_score, confidence, behavioral_indicators, protocol_diversity, communication_density)
    - Graph semantics (node_degree, weighted_degree, centrality_hint, node_priority)
    - Temporal (first_seen, last_seen, replay_sequence markers)
    """
    nodes = []
    for profile in host_profiles:
        node = GraphNode(
            node_id=_compute_node_id(profile.ip_address),
            ip_address=profile.ip_address,
            hostname=profile.hostname,
            inferred_role=profile.inferred_role,
            
            # Behavior
            risk_score=profile.risk_score,
            confidence=profile.confidence,
            behavioral_indicators=profile.behavioral_indicators,
            protocol_diversity=profile.protocol_diversity,
            communication_density=_compute_communication_density(profile),
            
            # Graph semantics (will be updated by graph metrics engine)
            node_degree=0,
            weighted_degree=0.0,
            centrality_hint=0.0,
            node_priority=0.0,
            
            # Temporal
            first_seen=profile.first_seen,
            last_seen=profile.last_seen,
            replay_sequence_start=profile.first_seen_sequence,
            replay_sequence_end=profile.last_seen_sequence,
            
            # Metadata
            metadata={
                "role_confidence": profile.role_confidence,
                "role_evidence": profile.role_evidence,
                "external_connections": profile.external_unique_hosts,
                "internal_connections": profile.internal_unique_hosts,
                "protocols": profile.protocols,
                "telemetry_completeness": profile.telemetry_completeness,
                "baseline_state": profile.baseline_state,
            }
        )
        nodes.append(node)
    
    return nodes


def build_graph_edges(relationships: List[HostRelationship]) -> List[GraphEdge]:
    """
    Convert relationships into graph-native edge entities.
    
    Each edge includes:
    - Identity (edge_id, source_node, target_node)
    - Relationship semantics (relationship_type, communication_pattern, directionality)
    - Behavior (relationship_risk, persistence_score, communication_density, protocol_diversity)
    - Temporal (first_seen, last_seen, replay_sequence markers)
    """
    edges = []
    for relationship in relationships:
        edge = GraphEdge(
            edge_id=relationship.edge_id,
            source_node=_compute_node_id(relationship.source),
            target_node=_compute_node_id(relationship.target),
            
            # Relationship semantics
            relationship_type=_infer_relationship_type(relationship),
            communication_pattern=_infer_communication_pattern(relationship),
            directionality=relationship.directionality,
            
            # Behavior
            relationship_risk=relationship.relationship_risk,
            persistence_score=relationship.persistence,
            communication_density=_compute_edge_communication_density(relationship),
            protocol_diversity=relationship.protocol_diversity,
            
            # Temporal
            first_seen=relationship.first_seen,
            last_seen=relationship.last_seen,
            replay_sequence_start=relationship.first_seen_sequence,
            replay_sequence_end=relationship.last_seen_sequence,
            
            # Metadata
            metadata={
                "severity": relationship.severity,
                "flows": relationship.flows,
                "packet_count": relationship.packet_count,
                "total_bytes": relationship.total_bytes,
                "protocols": relationship.protocols,
                "transports": relationship.transports,
                "persistence": relationship.persistence,
                "indicators": relationship.relationship_indicators,
                "graph_weight": relationship.graph_weight,
                "graph_edge_color": relationship.graph_edge_color,
                "graph_edge_width": relationship.graph_edge_width,
            }
        )
        edges.append(edge)
    
    return edges


def _compute_node_id(ip_address: str) -> str:
    """Compute stable node ID from IP address."""
    return sha256(f"node:{ip_address}".encode()).hexdigest()[:16]


def _compute_communication_density(profile: HostProfile) -> float:
    """
    Compute communication density for a node.
    Normalized ratio of connections to potential connections.
    """
    if profile.flow_count == 0:
        return 0.0
    
    # Simple heuristic: normalized flow count
    total_connections = profile.external_unique_hosts + profile.internal_unique_hosts
    if total_connections == 0:
        return 0.0
    
    # Normalize by log of connections (avoid extreme values)
    import math
    return round(min(profile.flow_count / (total_connections * 10 + 1), 1.0), 4)


def _compute_edge_communication_density(relationship: HostRelationship) -> float:
    """
    Compute communication density for an edge.
    Normalized ratio of packets/bytes to flow count.
    """
    if relationship.flows == 0:
        return 0.0
    
    # Simple heuristic: normalized packet count per flow
    density = relationship.packet_count / (relationship.flows * 5 + 1)
    return round(min(density, 1.0), 4)


def _infer_relationship_type(relationship: HostRelationship) -> str:
    """
    Infer relationship type from protocols and indicators.
    """
    indicators = set(relationship.relationship_indicators)
    
    if "persistent_tls_relationship" in indicators:
        return "persistent_tls"
    if "periodic_relationship_activity" in indicators:
        return "periodic_communication"
    if "periodic_low_volume_communication" in indicators:
        return "periodic_dns"
    if "elevated_flow_context" in indicators:
        return "suspicious_communication"
    
    # Default based on protocols
    if "dns" in relationship.protocols:
        return "periodic_dns"
    if "https" in relationship.protocols or "tls" in relationship.protocols:
        return "persistent_tls"
    if "smb" in relationship.protocols:
        return "smb_administrative"
    if "dhcp" in relationship.protocols:
        return "dhcp_assignment"
    
    return "interaction"


def _infer_communication_pattern(relationship: HostRelationship) -> str:
    """
    Infer communication pattern from flow characteristics.
    """
    if relationship.persistence >= 0.7:
        return "continuous"
    if relationship.persistence >= 0.4:
        return "periodic"
    if relationship.flows <= 3:
        return "sporadic"
    
    return "bursty"


def compute_graph_hashes(nodes: List[GraphNode], edges: List[GraphEdge]) -> Dict:
    """
    Compute stable hashes for future diff engine support.
    Enables deterministic comparison across snapshots.
    """
    # Compute individual node hashes
    node_hashes = {}
    for node in nodes:
        node_hash = sha256(
            f"{node.node_id}:{node.risk_score}:{node.behavioral_indicators}".encode()
        ).hexdigest()
        node_hashes[node.node_id] = node_hash
    
    # Compute individual edge hashes
    edge_hashes = {}
    for edge in edges:
        edge_hash = sha256(
            f"{edge.source_node}:{edge.target_node}:{edge.relationship_risk}".encode()
        ).hexdigest()
        edge_hashes[edge.edge_id] = edge_hash
    
    # Compute graph fingerprint (stable hash of all nodes and edges)
    all_hashes = sorted(list(node_hashes.values()) + list(edge_hashes.values()))
    graph_fingerprint = sha256("".join(all_hashes).encode()).hexdigest()
    
    return {
        "node_hashes": node_hashes,
        "edge_hashes": edge_hashes,
        "graph_fingerprint": graph_fingerprint,
    }
