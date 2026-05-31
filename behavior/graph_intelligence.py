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
from behavior.node_filters import is_non_investigative_node
from behavior.role_manager import INFRASTRUCTURE, normalize_role
from behavior.schemas import GraphEdge, GraphNode
from graph.community_classifier import classify_graph_nodes


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
    if is_non_investigative_node(node):
        return True
    
    # Suppress multicast range (224.0.0.0 - 239.255.255.255)
    # Suppress infrastructure-only roles
    if normalize_role(getattr(node, "role", node.inferred_role)) == INFRASTRUCTURE:
        # Check if this node only participates in infrastructure protocols
        protocols = set(node.metadata.get("protocols", []))
        infrastructure_only = {"dhcp", "dns", "ntp", "arp", "ldap"}
        if protocols and protocols.issubset(infrastructure_only):
            return True
    
    return False


def is_investigative_entity(node: GraphNode, edges: List[GraphEdge] = None) -> bool:
    """
    FIX 1: Determine if node is worth investigating.
    
    Returns False for:
    - Broadcast/multicast entities
    - Infrastructure-only entities
    - Nodes with no behavioral significance
    
    Infrastructure nodes may be returned, but they're de-prioritized.
    """
    # Reject pure broadcast/multicast
    if is_infrastructure_noise(node):
        return False
    
    # Accept nodes with meaningful behavioral signals
    if node.risk_score >= 5.0:
        return True
    
    # Accept nodes with external connections
    if node.metadata.get("external_connections", 0) > 0:
        return True
    
    # Accept nodes with behavioral indicators
    if node.behavioral_indicators:
        return True
    
    # Accept nodes with multiple protocols
    protocols = set(node.metadata.get("protocols", []))
    if len(protocols) > 2:
        return True
    
    # Infrastructure devices are borderline - include but low priority
    if normalize_role(getattr(node, "role", node.inferred_role)) == INFRASTRUCTURE:
        # Only if they have some significance
        if node.node_degree >= 2:
            return True
        return False
    
    return True


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
    FIX 2: Detect communities using behavioral classification.
    
    Classifies nodes into:
    - Domain Controllers
    - Servers
    - Workstations
    - External Services
    - Infrastructure
    - Unknown
    
    Returns dict of community_name -> [ip_addresses]
    """
    if not nodes:
        return {"Unknown": []}
    
    # Use behavioral classification instead of connectivity clustering
    return classify_graph_nodes(nodes, edges)


def _classify_node_behavior(
    node: GraphNode,
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> str:
    """
    FIX 2: Classify node into behavioral community.
    
    Returns:
    - Domain Controllers
    - Servers
    - Workstations
    - External Services
    - Infrastructure
    - Unknown
    """
    
    # Explicit role overrides
    if normalize_role(getattr(node, "role", node.inferred_role)) == INFRASTRUCTURE:
        return "Infrastructure"
    
    # Domain controller heuristics
    protocols = set(node.metadata.get("protocols", []))
    if any(p in protocols for p in ["ldap", "kerberos", "krb5", "msrpc"]):
        if node.node_degree > 5:  # Many connections
            return "Domain Controllers"
    
    # External service heuristics
    try:
        octets = [int(x) for x in node.ip_address.split(".")]
        # Check if external (simple heuristic: not 10.x, 172.16-31.x, 192.168.x)
        is_external = not (
            (octets[0] == 10) or
            (octets[0] == 172 and 16 <= octets[1] <= 31) or
            (octets[0] == 192 and octets[1] == 168)
        )
        
        if is_external:
            # External IPs with multiple internal consumers
            consumers = sum(1 for e in edges if e.target_node == node.node_id)
            if consumers >= 3 and ("https" in protocols or "tls" in protocols):
                return "External Services"
            elif consumers >= 2:
                return "External Services"
    except (ValueError, IndexError):
        pass
    
    # Server heuristics
    inbound_count = sum(1 for e in edges if e.target_node == node.node_id)
    outbound_count = sum(1 for e in edges if e.source_node == node.node_id)
    
    if inbound_count > outbound_count * 2 and inbound_count > 5:
        # More inbound than outbound = likely server
        return "Servers"
    
    # Workstation heuristics
    external_connections = node.metadata.get("external_connections", 0)
    if external_connections > 0 or outbound_count > inbound_count:
        # Workstations reach out more than they receive
        return "Workstations"
    
    return "Unknown"


def _classify_behavioral_communities(
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> Dict[str, List[str]]:
    """
    FIX 2: Classify all nodes into behavioral communities.
    
    Returns dict of community_name -> [ip_addresses]
    """
    communities = {
        "Domain Controllers": [],
        "Servers": [],
        "Workstations": [],
        "External Services": [],
        "Infrastructure": [],
        "Unknown": [],
    }
    
    for node in nodes:
        classification = _classify_node_behavior(node, nodes, edges)
        communities[classification].append(node.ip_address)
    
    # Remove empty communities
    communities = {k: v for k, v in communities.items() if v}
    
    return communities


# ============================================================================
# Behavioral Importance Modeling
# ============================================================================

def infer_external_service(
    node: GraphNode,
    edges: List[GraphEdge],
    nodes: List[GraphNode]
) -> Dict:
    """
    FIX 5: Identify if node is an external service.
    
    Conditions:
    - External IP
    - Multiple internal consumers
    - TLS service behavior
    - Stable service ports
    - Long-lived relationships
    
    Returns dict with:
    - is_external_service: bool
    - confidence: float
    - reason: str
    """
    try:
        octets = [int(x) for x in node.ip_address.split(".")]
        # Check if external (not 10.x, 172.16-31.x, 192.168.x)
        is_external_ip = not (
            (octets[0] == 10) or
            (octets[0] == 172 and 16 <= octets[1] <= 31) or
            (octets[0] == 192 and octets[1] == 168)
        )
    except (ValueError, IndexError):
        is_external_ip = False
    
    if not is_external_ip:
        return {
            "is_external_service": False,
            "confidence": 0.0,
            "reason": "internal_ip"
        }
    
    # Count internal consumers
    consumers = [e.source_node for e in edges if e.target_node == node.node_id]
    consumer_count = len(set(consumers))
    
    # Check protocols
    protocols = set(node.metadata.get("protocols", []))
    has_tls = any(p in protocols for p in ["https", "tls", "ssl"])
    has_service_behavior = bool(protocols)
    
    # Check persistence
    relationships = [e for e in edges if e.source_node == node.node_id or e.target_node == node.node_id]
    avg_persistence = (
        sum(r.persistence_score for r in relationships) / len(relationships)
        if relationships else 0.0
    )
    
    # Scoring
    score = 0.0
    reasons = []
    
    if consumer_count >= 3:
        score += 0.3
        reasons.append(f"{consumer_count}_consumers")
    elif consumer_count >= 2:
        score += 0.2
        reasons.append(f"{consumer_count}_consumers")
    
    if has_tls:
        score += 0.3
        reasons.append("tls_service")
    
    if has_service_behavior:
        score += 0.2
        reasons.append("service_protocols")
    
    if avg_persistence >= 0.5:
        score += 0.2
        reasons.append("persistent_relationships")
    
    is_service = score >= 0.5
    
    return {
        "is_external_service": is_service,
        "confidence": round(min(score, 1.0), 2),
        "reason": "|".join(reasons) if reasons else "low_signal"
    }


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
    FIX 3: Decompose graph-level risk into multiple components.
    
    Components:
    - host_risk: Average top node risk
    - relationship_risk: Risk from persistent/external relationships
    - community_risk: Risk from community structure anomalies
    - topology_risk: Risk from unusual connectivity patterns
    
    Returns dict of component_name -> risk_contribution
    """
    components = {}
    
    # Component 1: Host Risk (top 10% by risk)
    if nodes:
        sorted_by_risk = sorted(nodes, key=lambda n: n.risk_score, reverse=True)
        top_10_pct = max(1, len(nodes) // 10)
        high_risk_hosts = sorted_by_risk[:top_10_pct]
        host_risk = sum(h.risk_score for h in high_risk_hosts) / len(high_risk_hosts)
    else:
        host_risk = 0.0
    components["host_risk"] = round(host_risk * 0.4, 2)
    
    # Component 2: Relationship Risk
    if edges:
        # Persistent external relationships
        external_edges = [
            e for e in edges if e.relationship_type in 
            ["persistent_tls", "external_tls_session", "directory_authentication", "administrative_rpc"]
        ]
        if external_edges:
            avg_persistence = sum(e.persistence_score for e in external_edges) / len(external_edges)
            avg_risk = sum(e.relationship_risk for e in external_edges) / len(external_edges)
            rel_risk = avg_persistence * avg_risk
        else:
            rel_risk = 0.0
        
        # Periodic behaviors (beaconing-like)
        periodic_edges = [e for e in edges if e.communication_pattern == "periodic"]
        if periodic_edges:
            periodic_risk = sum(e.relationship_risk for e in periodic_edges) / len(periodic_edges)
        else:
            periodic_risk = 0.0
        
        relationship_risk = max(rel_risk, periodic_risk)
    else:
        relationship_risk = 0.0
    components["relationship_risk"] = round(relationship_risk * 0.25, 2)
    
    # Component 3: Community Risk
    # Risk concentration in specific communities
    if nodes:
        communities = detect_behavioral_communities(nodes, edges)
        community_risk_scores = []
        
        for community_name, ips in communities.items():
            community_nodes = [n for n in nodes if n.ip_address in ips]
            if community_nodes:
                avg_community_risk = sum(n.risk_score for n in community_nodes) / len(community_nodes)
                community_risk_scores.append(avg_community_risk)
        
        # Penalize if risk is concentrated in one community
        if community_risk_scores:
            max_risk = max(community_risk_scores)
            risk_concentration = max_risk / (sum(community_risk_scores) / len(community_risk_scores) + 0.01)
            community_risk = min(risk_concentration * 2, 100.0)  # Normalize
        else:
            community_risk = 0.0
    else:
        community_risk = 0.0
    components["community_risk"] = round(community_risk * 0.2, 2)
    
    # Component 4: Topology Risk
    # Unusual fanout, isolated risky nodes, etc.
    if nodes and edges:
        # High fanout risk
        external_connections = sum(n.metadata.get("external_connections", 0) for n in nodes)
        fanout_risk = min(external_connections / 100.0, 1.0) * 25.0
        
        # Isolated risky nodes
        nodes_with_edges = set()
        for edge in edges:
            nodes_with_edges.add(edge.source_node)
            nodes_with_edges.add(edge.target_node)
        
        isolated_risky = sum(
            1 for n in nodes 
            if n.node_id not in nodes_with_edges and n.risk_score >= 20
        )
        isolation_risk = isolated_risky * 5.0
        
        topology_risk = max(fanout_risk, isolation_risk)
    else:
        topology_risk = 0.0
    components["topology_risk"] = round(topology_risk * 0.15, 2)
    
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
    FIX 7: Compute graph-wide behavioral health metrics.
    
    Includes:
    - avg_node_risk
    - avg_edge_persistence
    - externality_ratio
    - infrastructure_ratio
    - suspicious_edge_ratio
    - avg_protocol_diversity
    - isolated_node_ratio
    - community_balance_score (FIX 7)
    - relationship_diversity_score (FIX 7)
    - external_dependency_score (FIX 7)
    - risk_concentration_score (FIX 7)
    
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
            "community_balance_score": 0.0,
            "relationship_diversity_score": 0.0,
            "external_dependency_score": 0.0,
            "risk_concentration_score": 0.0,
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
    infra_count = sum(1 for n in nodes if normalize_role(getattr(n, "role", n.inferred_role)) == INFRASTRUCTURE)
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
    
    # FIX 7: Community balance score (how evenly distributed are nodes across communities)
    communities = detect_behavioral_communities(nodes, edges)
    if communities:
        community_sizes = [len(ips) for ips in communities.values()]
        avg_size = sum(community_sizes) / len(community_sizes)
        # Gini coefficient-like metric (0 = perfect balance, 1 = all in one)
        if avg_size > 0:
            variance = sum((size - avg_size) ** 2 for size in community_sizes) / len(community_sizes)
            max_variance = avg_size ** 2
            balance = 1.0 - (variance / (max_variance + 0.01))
        else:
            balance = 1.0
    else:
        balance = 0.0
    metrics["community_balance_score"] = round(max(0.0, min(balance, 1.0)), 2)
    
    # FIX 7: Relationship diversity score (how many different relationship types)
    if edges:
        rel_types = len(set(e.relationship_type for e in edges))
        max_rel_types = 12  # Approximate max from _infer_relationship_type
        rel_diversity = rel_types / max_rel_types
    else:
        rel_diversity = 0.0
    metrics["relationship_diversity_score"] = round(rel_diversity, 2)
    
    # FIX 7: External dependency score (how much depends on external services)
    external_services = [
        n for n in nodes 
        if infer_external_service(n, edges, nodes)["is_external_service"]
    ]
    if external_services:
        # Count unique internal nodes that connect to external services
        internal_consumers = set()
        for ext_node in external_services:
            consumers = [e.source_node for e in edges if e.target_node == ext_node.node_id]
            internal_consumers.update(consumers)
        
        dependency = len(internal_consumers) / len(nodes)
    else:
        dependency = 0.0
    metrics["external_dependency_score"] = round(dependency, 2)
    
    # FIX 7: Risk concentration score (how concentrated is risk in few nodes)
    if nodes:
        sorted_risks = sorted([n.risk_score for n in nodes], reverse=True)
        top_20_pct = max(1, len(nodes) // 5)
        top_risk = sum(sorted_risks[:top_20_pct])
        total_risk = sum(sorted_risks)
        if total_risk > 0:
            concentration = top_risk / total_risk
        else:
            concentration = 0.0
    else:
        concentration = 0.0
    metrics["risk_concentration_score"] = round(concentration, 2)
    
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
