"""
Layer 4: Graph Metrics Engine
Computes lightweight graph metrics for topology analysis.
Keeps replay-safe and avoids expensive graph algorithms.
"""

from typing import Dict, List

from behavior.schemas import GraphEdge, GraphNode, GraphState


def compute_graph_metrics(
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> Dict:
    """
    Compute lightweight graph metrics.
    
    Returns:
    - Node metrics (degree, weighted_degree, centrality_hint)
    - Edge metrics (persistence, communication_density, intensity)
    - Graph metrics (density, isolated_nodes, connected_components, suspicious_clusters)
    """
    # Build adjacency for quick lookups
    node_map = {node.node_id: node for node in nodes}
    edge_map = {}
    
    for edge in edges:
        if edge.source_node not in edge_map:
            edge_map[edge.source_node] = {"outbound": [], "inbound": []}
        if edge.target_node not in edge_map:
            edge_map[edge.target_node] = {"outbound": [], "inbound": []}
        
        edge_map[edge.source_node]["outbound"].append(edge)
        edge_map[edge.target_node]["inbound"].append(edge)
    
    # Compute node metrics
    _compute_node_metrics(nodes, edge_map, node_map)
    
    # Compute edge metrics
    _compute_edge_metrics(edges)
    
    # Compute graph metrics
    graph_metrics = _compute_graph_metrics(nodes, edges)
    
    return graph_metrics


def _compute_node_metrics(
    nodes: List[GraphNode],
    edge_map: Dict,
    node_map: Dict
) -> None:
    """Compute per-node metrics and update nodes in place."""
    
    for node in nodes:
        node_id = node.node_id
        outbound_edges = edge_map.get(node_id, {}).get("outbound", [])
        inbound_edges = edge_map.get(node_id, {}).get("inbound", [])
        
        # Node degree = number of unique neighbors
        neighbors = set()
        for edge in outbound_edges + inbound_edges:
            if edge.source_node == node_id:
                neighbors.add(edge.target_node)
            else:
                neighbors.add(edge.source_node)
        
        node.node_degree = len(neighbors)
        
        # Weighted degree = sum of edge weights
        weighted_degree = 0.0
        for edge in outbound_edges + inbound_edges:
            weight = edge.metadata.get("graph_weight", 1.0)
            weighted_degree += weight
        
        node.weighted_degree = round(weighted_degree, 4)
        
        # Centrality hint = normalized degree * risk signal
        max_degree = max(1, max((n.node_degree for n in nodes), default=1))
        degree_norm = node.node_degree / max_degree
        risk_signal = min(node.risk_score / 100.0, 1.0)
        node.centrality_hint = round(degree_norm * 0.6 + risk_signal * 0.4, 4)
        
        # Node priority = risk + centrality
        node.node_priority = round(node.risk_score * 0.5 + node.centrality_hint * 50, 4)
        
        # Communication density already computed by graph_builder, but refine it
        if node.node_degree > 0:
            node.communication_density = round(node.weighted_degree / (node.node_degree + 1), 4)


def _compute_edge_metrics(edges: List[GraphEdge]) -> None:
    """Compute per-edge metrics and update edges in place."""
    
    for edge in edges:
        # Persistence score already set from relationship, just normalize
        edge.persistence_score = round(min(edge.persistence_score, 1.0), 4)
        
        # Communication density already computed, just ensure it's normalized
        edge.communication_density = round(min(edge.communication_density, 1.0), 4)


def _compute_graph_metrics(nodes: List[GraphNode], edges: List[GraphEdge]) -> Dict:
    """Compute graph-level metrics."""
    
    if not nodes:
        return {
            "node_count": 0,
            "edge_count": 0,
            "graph_density": 0.0,
            "graph_risk_score": 0.0,
            "isolated_node_count": 0,
            "high_centrality_nodes": [],
            "relationship_types": [],
            "avg_node_degree": 0.0,
            "suspicious_edges": 0,
        }
    
    # Count isolated nodes
    nodes_with_edges = set()
    for edge in edges:
        nodes_with_edges.add(edge.source_node)
        nodes_with_edges.add(edge.target_node)
    
    isolated_nodes = [n for n in nodes if n.node_id not in nodes_with_edges]
    
    # Compute graph density
    # density = actual_edges / possible_edges
    # For directed graph: possible_edges = n * (n - 1)
    n = len(nodes)
    possible_edges = max(1, n * (n - 1))
    graph_density = round(len(edges) / possible_edges, 6)
    
    # Compute average degree
    avg_degree = round(sum(n.node_degree for n in nodes) / len(nodes), 2)
    
    # Compute graph risk score (average of top node risks)
    sorted_nodes = sorted(nodes, key=lambda n: n.risk_score, reverse=True)
    top_risk_nodes = sorted_nodes[:max(1, len(nodes) // 10)]
    graph_risk_score = round(sum(n.risk_score for n in top_risk_nodes) / len(top_risk_nodes), 2)
    
    # Find high centrality nodes
    sorted_by_centrality = sorted(nodes, key=lambda n: n.centrality_hint, reverse=True)
    high_centrality_nodes = [n.ip_address for n in sorted_by_centrality[:5]]
    
    # Collect relationship types
    relationship_types = sorted(set(e.relationship_type for e in edges))
    
    # Count suspicious edges
    suspicious_edges = sum(1 for e in edges if e.relationship_risk >= 35)
    
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "graph_density": graph_density,
        "graph_risk_score": graph_risk_score,
        "isolated_node_count": len(isolated_nodes),
        "high_centrality_nodes": high_centrality_nodes,
        "relationship_types": relationship_types,
        "avg_node_degree": avg_degree,
        "suspicious_edges": suspicious_edges,
    }


def compute_community_detection(
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> Dict[str, List[str]]:
    """
    Lightweight community detection using node connectivity.
    Groups nodes by simple connectivity clustering (no expensive algorithms).
    """
    # Build adjacency
    adjacency = {}
    for node in nodes:
        adjacency[node.node_id] = set()
    
    for edge in edges:
        adjacency[edge.source_node].add(edge.target_node)
        adjacency[edge.target_node].add(edge.source_node)
    
    # Simple clustering: find connected components
    visited = set()
    communities = {}
    community_id = 0
    
    for node_id in adjacency:
        if node_id in visited:
            continue
        
        # BFS to find connected component
        queue = [node_id]
        component = set()
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            
            visited.add(current)
            component.add(current)
            
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    queue.append(neighbor)
        
        communities[f"community_{community_id}"] = list(component)
        community_id += 1
    
    return communities
