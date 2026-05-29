"""
Layer 4: Graph Intelligence Engine
Enhances graph-native analytics with behavioral intelligence.
- Centrality suppression (infrastructure noise filtering)
- Improved community detection
- Behavioral importance modeling
- Explainable risk attribution
- Relationship semantic enrichment
- Graph health metrics
"""

from typing import Dict, List, Set, Tuple
from behavior.schemas import GraphEdge, GraphNode


# ============================================================================
# Centrality Suppression Architecture
# ============================================================================

INFRASTRUCTURE_NOISE_PATTERNS = {
    # Broadcast/multicast/bootstrap entities that pollute centrality rankings
    "broadcast_addresses": {
        "0.0.0.0",           # Bootstrap broadcast
        "255.255.255.255",   # Broadcast
        "224.0.0.0/4",       # Multicast range (simplified)
    },
    "infrastructure_only_nodes": {
        "dhcp",              # DHCP servers (via role inference)
        "dns",               # DNS servers
        "ntp",               # NTP servers
    },
    "discovery_only_nodes": {
        "mdns",              # mDNS chatter
        "llmnr",             # LLMNR broadcast
        "ssdp",              # UPnP discovery
        "nbns",              # NetBIOS broadcast
    }
}


def is_infrastructure_noise(node: GraphNode) -> bool:
    """
    Determine if node is infrastructure noise that should be suppressed from
    centrality rankings.
    
    Returns True if node should be downweighted/suppressed.
    """
    # Suppress special addresses
    ip = node.ip_address
    if ip in INFRASTRUCTURE_NOISE_PATTERNS["broadcast_addresses"]:
        return True
    
    # Suppress multicast range (224.0.0.0 - 239.255.255.255)
    try:
        octets = [int(x) for x in ip.split(".")]
        if octets[0] in range(224, 240):
            return True
    except (ValueError, IndexError):
        pass
    
    # Suppress infrastructure-only roles
    if node.inferred_role == "infrastructure_device":
        # Check if this node only participates in infrastructure protocols
        protocols = set(node.metadata.get("protocols", []))
        infrastructure_only = {"dhcp", "dns", "ntp", "arp", "ldap"}
        if protocols and protocols.issubset(infrastructure_only):
            return True
    
    return False


def compute_behavioral_centrality(
    node: GraphNode,
    nodes: List[GraphNode],
    edges: List[GraphEdge],
    suppress_noise: bool = True
) -> float:
    """
    Compute behavioral centrality that combines:
    - Network connectivity (degree)
    - Behavioral risk
    - Externality (connections to external hosts)
    - Relationship diversity
    - Protocol diversity
    
    NOT pure degree centrality.
    """
    if suppress_noise and is_infrastructure_noise(node):
        # Heavily suppress infrastructure noise
        return 0.05
    
    # Build adjacency for this node
    outbound_edges = [e for e in edges if e.source_node == node.node_id]
    inbound_edges = [e for e in edges if e.target_node == node.node_id]
    all_edges = outbound_edges + inbound_edges
    
    if not all_edges:
        return 0.0
    
    # Component 1: Connectivity (normalized degree)
    degree = len(set(
        [e.target_node for e in outbound_edges] +
        [e.source_node for e in inbound_edges]
    ))
    max_degree = max(1, max(n.node_degree for n in nodes) if nodes else 1)
    degree_component = (degree / max_degree) * 0.2
    
    # Component 2: Risk signal
    risk_component = min(node.risk_score / 100.0, 1.0) * 0.3
    
    # Component 3: Relationship diversity
    rel_types = set(e.relationship_type for e in all_edges)
    rel_diversity = len(rel_types) / 8.0  # Normalize to ~8 possible types
    rel_component = min(rel_diversity, 1.0) * 0.2
    
    # Component 4: Protocol diversity
    protocol_diversity = min(node.protocol_diversity / 10.0, 1.0) * 0.15
    
    # Component 5: Externality (external connections boost importance)
    external_count = node.metadata.get("external_connections", 0)
    externality = min(external_count / 50.0, 1.0) * 0.15
    
    centrality = (degree_component + risk_component + rel_component + 
                  protocol_diversity + externality)
    
    return round(min(centrality, 1.0), 4)


# ============================================================================
# Improved Community Detection
# ============================================================================

def detect_behavioral_communities(
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> Dict[str, List[str]]:
    """
    Detect communities using weighted community detection.
    Accounts for:
    - Network connectivity (structure)
    - Relationship types (semantics)
    - Host roles (behavior)
    - Protocol usage (semantics)
    
    Returns dict of community_name -> [ip_addresses]
    """
    if not nodes or not edges:
        return {"ungrouped": [n.ip_address for n in nodes]}
    
    # Phase 1: Role-based grouping (semantic)
    role_groups = _group_by_role(nodes)
    
    # Phase 2: Connectivity clustering (structural)
    connectivity_groups = _detect_connectivity_communities(nodes, edges)
    
    # Phase 3: Merge and refine
    final_communities = _merge_communities(role_groups, connectivity_groups, edges)
    
    return final_communities


def _group_by_role(nodes: List[GraphNode]) -> Dict[str, List[str]]:
    """Group nodes by inferred role."""
    groups = {}
    
    for node in nodes:
        role = node.inferred_role or "unknown"
        if role not in groups:
            groups[role] = []
        groups[role].append(node.ip_address)
    
    return groups


def _detect_connectivity_communities(
    nodes: List[GraphNode],
    edges: List[GraphEdge],
    max_iterations: int = 10
) -> Dict[str, List[str]]:
    """
    Simple label propagation for connectivity-based communities.
    Not expensive, but effective for network topology.
    """
    node_map = {node.node_id: node for node in nodes}
    
    # Build adjacency
    adjacency = {node.node_id: set() for node in nodes}
    for edge in edges:
        adjacency[edge.source_node].add(edge.target_node)
        adjacency[edge.target_node].add(edge.source_node)
    
    # Initialize labels
    labels = {node.node_id: idx for idx, node in enumerate(nodes)}
    
    # Propagate labels
    for iteration in range(max_iterations):
        new_labels = labels.copy()
        for node_id in labels:
            neighbors = adjacency.get(node_id, set())
            if neighbors:
                neighbor_labels = [labels[n] for n in neighbors if n in labels]
                if neighbor_labels:
                    # Choose most common neighbor label
                    new_labels[node_id] = max(
                        set(neighbor_labels),
                        key=neighbor_labels.count
                    )
        
        if new_labels == labels:
            break
        labels = new_labels
    
    # Group by label
    communities = {}
    for node in nodes:
        label = labels.get(node.node_id, 0)
        label_key = f"connectivity_{label}"
        if label_key not in communities:
            communities[label_key] = []
        communities[label_key].append(node.ip_address)
    
    return communities


def _merge_communities(
    role_groups: Dict[str, List[str]],
    connectivity_groups: Dict[str, List[str]],
    edges: List[GraphEdge]
) -> Dict[str, List[str]]:
    """
    Merge role-based and connectivity-based groupings.
    Prefer semantic grouping when clear, use connectivity otherwise.
    """
    result = {}
    
    # Semantic grouping from roles
    semantic_names = {
        "infrastructure_device": "Infrastructure",
        "server": "Servers",
        "workstation": "Workstations",
        "unknown": "Ungrouped"
    }
    
    for role, ips in role_groups.items():
        group_name = semantic_names.get(role, role)
        result[group_name] = ips
    
    return result


# ============================================================================
# Behavioral Importance Modeling
# ============================================================================

def compute_behavioral_importance(
    node: GraphNode,
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> float:
    """
    Compute behavioral importance combining multiple factors.
    
    Factors:
    - Risk score (behavioral signal)
    - Relationship diversity (hub-like importance)
    - External connectivity (outbound reach)
    - Persistence (long-lived relationships)
    - Protocol diversity (capability diversity)
    """
    # Component 1: Risk (directly indicates importance)
    risk_component = min(node.risk_score / 100.0, 1.0) * 0.25
    
    # Component 2: Relationship diversity
    rel_edges = [e for e in edges if e.source_node == node.node_id or e.target_node == node.node_id]
    rel_types = len(set(e.relationship_type for e in rel_edges))
    rel_component = min(rel_types / 8.0, 1.0) * 0.2
    
    # Component 3: External connectivity
    external_conns = node.metadata.get("external_connections", 0)
    external_component = min(external_conns / 100.0, 1.0) * 0.25
    
    # Component 4: Persistence (average edge persistence)
    if rel_edges:
        avg_persistence = sum(e.persistence_score for e in rel_edges) / len(rel_edges)
    else:
        avg_persistence = 0.0
    persistence_component = avg_persistence * 0.15
    
    # Component 5: Protocol diversity
    protocol_component = min(node.protocol_diversity / 10.0, 1.0) * 0.15
    
    importance = (risk_component + rel_component + external_component + 
                  persistence_component + protocol_component)
    
    return round(min(importance, 1.0), 4)


# ============================================================================
# Explainable Graph Risk Decomposition
# ============================================================================

def decompose_graph_risk(
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> Dict[str, float]:
    """
    Decompose graph-level risk score into explainable components.
    
    Returns dict of component_name -> risk_contribution
    """
    components = {}
    
    # Component 1: High-risk hosts (top 10% by risk)
    sorted_by_risk = sorted(nodes, key=lambda n: n.risk_score, reverse=True)
    top_10_pct = max(1, len(nodes) // 10)
    high_risk_hosts = sorted_by_risk[:top_10_pct]
    high_risk_score = sum(h.risk_score for h in high_risk_hosts) / len(high_risk_hosts)
    components["high_risk_hosts"] = round(high_risk_score * 0.4, 2)
    
    # Component 2: Persistent external relationships
    external_edges = [e for e in edges if e.relationship_type in 
                      ["persistent_tls", "external_tls_session"]]
    if external_edges:
        avg_persistence = sum(e.persistence_score for e in external_edges) / len(external_edges)
        external_risk = avg_persistence * sum(e.relationship_risk for e in external_edges) / len(external_edges)
    else:
        external_risk = 0.0
    components["persistent_external"] = round(external_risk * 0.25, 2)
    
    # Component 3: Periodic behaviors (beaconing-like)
    periodic_edges = [e for e in edges if e.communication_pattern == "periodic"]
    if periodic_edges:
        periodic_risk = sum(e.relationship_risk for e in periodic_edges) / len(periodic_edges)
    else:
        periodic_risk = 0.0
    components["periodic_communication"] = round(periodic_risk * 0.2, 2)
    
    # Component 4: High relationship density / fanout
    avg_degree = sum(n.node_degree for n in nodes) / len(nodes) if nodes else 0
    externality_sum = sum(n.metadata.get("external_connections", 0) for n in nodes)
    fanout_risk = min(externality_sum / 1000.0, 1.0) * 25.0
    components["external_fanout"] = round(fanout_risk * 0.15, 2)
    
    return components


# ============================================================================
# Snapshot Quality Validation
# ============================================================================

def compute_snapshot_quality(
    node_count: int,
    edge_count: int,
    prev_node_count: int = None,
    prev_edge_count: int = None
) -> float:
    """
    Compute quality score for a temporal snapshot.
    
    Considers:
    - Non-empty content (nodes and edges)
    - Not purely redundant (different from previous)
    - Reasonable density (not noise)
    
    Returns 0-1 quality score.
    """
    # Empty snapshot = low quality
    if node_count == 0 or edge_count == 0:
        return 0.0
    
    # Redundant snapshot = moderate quality
    if prev_node_count is not None and prev_edge_count is not None:
        if node_count == prev_node_count and edge_count == prev_edge_count:
            return 0.3
    
    # Reasonable snapshot = high quality
    # Expect at least some structure (edges > 0)
    if edge_count > 0:
        # Penalize if too sparse (no edges for many nodes)
        min_edges_expected = max(1, node_count - 1)
        if edge_count < min_edges_expected:
            return 0.6
        return 1.0
    
    return 0.7


# ============================================================================
# Graph Health Metrics
# ============================================================================

def compute_graph_health_metrics(
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> Dict[str, float]:
    """
    Compute graph-wide behavioral health metrics.
    
    Returns metrics useful for:
    - Dashboard reporting
    - Anomaly detection
    - Trend analysis
    """
    metrics = {}
    
    if not nodes:
        return {
            "avg_node_risk": 0.0,
            "avg_edge_persistence": 0.0,
            "externality_ratio": 0.0,
            "infrastructure_ratio": 0.0,
            "suspicious_edge_ratio": 0.0,
            "avg_protocol_diversity": 0.0,
            "isolated_node_ratio": 0.0,
        }
    
    # Average node risk
    metrics["avg_node_risk"] = round(
        sum(n.risk_score for n in nodes) / len(nodes), 2
    )
    
    # Average edge persistence
    if edges:
        metrics["avg_edge_persistence"] = round(
            sum(e.persistence_score for e in edges) / len(edges), 4
        )
    else:
        metrics["avg_edge_persistence"] = 0.0
    
    # Externality ratio (external connections / total potential)
    total_external = sum(n.metadata.get("external_connections", 0) for n in nodes)
    metrics["externality_ratio"] = round(
        total_external / max(1, len(nodes) * 10), 4
    )
    
    # Infrastructure ratio (infrastructure nodes / total)
    infra_count = sum(1 for n in nodes if n.inferred_role == "infrastructure_device")
    metrics["infrastructure_ratio"] = round(infra_count / len(nodes), 4)
    
    # Suspicious edge ratio
    if edges:
        suspicious = sum(1 for e in edges if e.relationship_risk >= 35)
        metrics["suspicious_edge_ratio"] = round(suspicious / len(edges), 4)
    else:
        metrics["suspicious_edge_ratio"] = 0.0
    
    # Average protocol diversity
    metrics["avg_protocol_diversity"] = round(
        sum(n.protocol_diversity for n in nodes) / len(nodes), 2
    )
    
    # Isolated node ratio (nodes with no edges)
    isolated = sum(1 for n in nodes if n.node_degree == 0)
    metrics["isolated_node_ratio"] = round(isolated / len(nodes), 4)
    
    return metrics


# ============================================================================
# Stable Graph Fingerprinting (Layer 5 Preparation)
# ============================================================================

def compute_stable_graph_fingerprint(
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> Dict[str, str]:
    """
    Compute stable fingerprints for:
    - Individual node hashing
    - Individual edge hashing
    - Complete graph hashing
    - Snapshot lineage tracking
    
    Enables future diff engine (Layer 5) to:
    - Detect node emergence
    - Detect relationship emergence
    - Detect risk escalation
    - Detect topology evolution
    """
    from hashlib import sha256
    
    fingerprints = {}
    
    # Node hashes (based on identity + behavioral state)
    node_hashes = []
    for node in sorted(nodes, key=lambda n: n.node_id):
        # Stable hash: node_id + risk + indicators + protocols
        indicators_str = ",".join(sorted(node.behavioral_indicators))
        protocols_str = ",".join(sorted(node.metadata.get("protocols", [])))
        content = f"{node.node_id}:{node.risk_score}:{indicators_str}:{protocols_str}"
        node_hash = sha256(content.encode()).hexdigest()[:16]
        node_hashes.append(node_hash)
        fingerprints[f"node_{node.ip_address}"] = node_hash
    
    # Edge hashes (based on source + target + type + risk)
    edge_hashes = []
    for edge in sorted(edges, key=lambda e: e.edge_id):
        # Stable hash: source + target + type + risk
        content = f"{edge.source_node}:{edge.target_node}:{edge.relationship_type}:{edge.relationship_risk}"
        edge_hash = sha256(content.encode()).hexdigest()[:16]
        edge_hashes.append(edge_hash)
        fingerprints[f"edge_{edge.edge_id}"] = edge_hash
    
    # Graph fingerprint (overall topology hash)
    all_hashes = sorted(node_hashes + edge_hashes)
    graph_content = "|".join(all_hashes)
    graph_fingerprint = sha256(graph_content.encode()).hexdigest()
    fingerprints["graph_fingerprint"] = graph_fingerprint
    
    return fingerprints
