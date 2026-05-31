"""
Layer 4: Graph Builder (HARDENED)
Converts host profiles and relationships into graph-native node and edge entities.

FIXES:
- Expand _infer_relationship_type with 7 new semantic types
- Add protocol-based relationship classification
- Support directory_authentication, administrative_rpc, infrastructure_dns, etc.
"""

from hashlib import sha256
from typing import Dict, List, Optional

from behavior.schemas import GraphEdge, GraphNode, HostProfile, HostRelationship


def build_graph_nodes(host_profiles: List[HostProfile]) -> List[GraphNode]:
    """
    Convert host profiles into graph-native node entities.
    """
    nodes = []
    for profile in host_profiles:
        node = GraphNode(
            node_id=_compute_node_id(profile.ip_address),
            ip_address=profile.ip_address,
            hostname=profile.hostname,
            inferred_role=profile.role,
            role=profile.role,
            
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
    """
    edges = []
    for relationship in relationships:
        edge = GraphEdge(
            edge_id=relationship.edge_id,
            source_node=_compute_node_id(relationship.source),
            target_node=_compute_node_id(relationship.target),
            
            # Relationship semantics (HARDENED with expanded types)
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
    """Compute communication density for a node."""
    if profile.flow_count == 0:
        return 0.0
    
    total_connections = profile.external_unique_hosts + profile.internal_unique_hosts
    if total_connections == 0:
        return 0.0
    
    return round(min(profile.flow_count / (total_connections * 10 + 1), 1.0), 4)


def _compute_edge_communication_density(relationship: HostRelationship) -> float:
    """Compute communication density for an edge."""
    if relationship.flows == 0:
        return 0.0
    
    density = relationship.packet_count / (relationship.flows * 5 + 1)
    return round(min(density, 1.0), 4)


def _infer_relationship_type(relationship: HostRelationship) -> str:
    """
    Infer relationship type from protocols and indicators (HARDENED).
    
    FIX 8: Expanded relationship semantics support:
    - directory_authentication (LDAP, Kerberos)
    - administrative_rpc (MS-RPC, NetBIOS)
    - infrastructure_dns (DNS queries)
    - interactive_http (HTTP, web browsing)
    - external_tls_session (HTTPS, persistent TLS)
    - file_transfer (SMB, SFTP, FTP)
    - service_discovery (mDNS, SSDP, DNS-SD)
    - persistent_tls (legacy)
    - periodic_communication (legacy)
    - periodic_dns (legacy)
    - suspicious_communication (detected anomaly)
    - interaction (default)
    """
    indicators = set(relationship.relationship_indicators)
    protocols = set(relationship.protocols)
    
    # Check indicators first
    if "persistent_tls_relationship" in indicators:
        return "persistent_tls"
    if "periodic_relationship_activity" in indicators:
        return "periodic_communication"
    if "periodic_low_volume_communication" in indicators:
        return "periodic_dns"
    if "elevated_flow_context" in indicators:
        return "suspicious_communication"
    
    # FIX 8: Expanded protocol-based mapping
    
    # Directory authentication (LDAP, Kerberos)
    if any(p in protocols for p in ["ldap", "kerberos", "krb5"]):
        return "directory_authentication"
    
    # Administrative RPC (MS-RPC, NetBIOS)
    if any(p in protocols for p in ["msrpc", "netbios", "epmap"]):
        return "administrative_rpc"
    
    # Infrastructure DNS
    if "dns" in protocols:
        return "infrastructure_dns"
    
    # Interactive HTTP (HTTP without persistence)
    if "http" in protocols and relationship.persistence < 0.4:
        return "interactive_http"
    
    # External TLS sessions
    if ("https" in protocols or "tls" in protocols) and relationship.persistence >= 0.4:
        return "external_tls_session"
    
    # File transfer (SMB, SFTP, FTP)
    if any(p in protocols for p in ["smb", "sftp", "ftp", "cifs"]):
        return "file_transfer"
    
    # Service discovery (mDNS, SSDP, DNS-SD)
    if any(p in protocols for p in ["mdns", "ssdp", "dns-sd"]):
        return "service_discovery"
    
    # DHCP assignment
    if "dhcp" in protocols:
        return "dhcp_assignment"
    
    # Default fallback to legacy types for backward compatibility
    if "dns" in protocols:
        return "periodic_dns"
    if "https" in protocols or "tls" in protocols:
        return "persistent_tls"
    if "smb" in protocols:
        return "file_transfer"
    
    return "interaction"


def _infer_communication_pattern(relationship: HostRelationship) -> str:
    """Infer communication pattern from flow characteristics."""
    if relationship.persistence >= 0.7:
        return "continuous"
    if relationship.persistence >= 0.4:
        return "periodic"
    if relationship.flows <= 3:
        return "sporadic"
    
    return "bursty"


def compute_stable_graph_fingerprint(
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> Dict[str, str]:
    """
    FIX 7: This function is DEPRECATED.
    
    Use graph_intelligence.compute_stable_graph_fingerprint() instead.
    
    Kept here only for backward compatibility during transition.
    This will be removed in a future update.
    """
    from behavior.graph_intelligence import compute_stable_graph_fingerprint as compute_fp
    return compute_fp(nodes, edges)


# Deprecated function - kept for transition period
def compute_graph_hashes(nodes: List[GraphNode], edges: List[GraphEdge]) -> Dict:
    """
    FIX 7: DEPRECATED - DO NOT USE
    
    This function is superseded by compute_stable_graph_fingerprint from graph_intelligence.
    
    Use graph_intelligence.compute_stable_graph_fingerprint() instead.
    """
    import warnings
    warnings.warn(
        "compute_graph_hashes is deprecated. Use graph_intelligence.compute_stable_graph_fingerprint instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from behavior.graph_intelligence import compute_stable_graph_fingerprint as compute_fp
    return compute_fp(nodes, edges)
