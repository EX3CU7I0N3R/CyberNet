"""
Layer 4: Graph Metrics Engine (HARDENED)
Computes lightweight graph metrics for topology analysis.
Keeps replay-safe and avoids expensive graph algorithms.

FIXES:
- Replace legacy centrality with behavioral centrality from graph_intelligence
- Suppress infrastructure noise in centrality rankings
- Add infrastructure noise filtering
"""

from typing import Dict, List

from behavior.graph_intelligence import (
    compute_behavioral_centrality,
    is_infrastructure_noise,
)
from behavior.node_filters import is_non_investigative_node
from behavior.schemas import GraphEdge, GraphNode, GraphState


def compute_graph_metrics(
    nodes: List[GraphNode],
    edges: List[GraphEdge]
) -> Dict:
    """
    Compute lightweight graph metrics (HARDENED).
    
    Changes:
    - Behavioral centrality replaces topology-only centrality
    - Infrastructure noise is suppressed from rankings
    - Node priority uses behavioral importance
    
    Returns:
    - Node metrics (degree, weighted_degree, behavioral_centrality)
    - Edge metrics (persistence, communication_density)
    - Graph metrics (density, isolated_nodes, suspicious_clusters)
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
    
    # Compute node metrics (with behavioral centrality)
    _compute_node_metrics(nodes, edges, edge_map, node_map)
    
    # Compute edge metrics
    _compute_edge_metrics(edges)
    
    # Compute graph metrics (with noise suppression)
    graph_metrics = _compute_graph_metrics(nodes, edges)
    
    return graph_metrics


def _compute_node_metrics(
    nodes: List[GraphNode],
    edges: List[GraphEdge],
    edge_map: Dict,
    node_map: Dict
) -> None:
    """Compute per-node metrics with behavioral centrality (HARDENED)."""
    
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
        
        # FIX 1: Use behavioral centrality instead of topology-only centrality
        # Accounts for: degree + risk + externality + relationship diversity + protocol diversity
        node.centrality_hint = compute_behavioral_centrality(
            node=node,
            nodes=nodes,
            edges=edges,
            suppress_noise=True
        )
        
        # FIX 2: Recalculate node priority using behavioral importance
        # node_priority = (risk * 0.4) + (centrality * 60)
        node.node_priority = round(
            (node.risk_score * 0.4) + (node.centrality_hint * 60),
            4
        )
        
        # Communication density already computed by graph_builder, refine it
        if node.node_degree > 0:
            node.communication_density = round(
                node.weighted_degree / (node.node_degree + 1), 4
            )


def _compute_edge_metrics(edges: List[GraphEdge]) -> None:
    """Compute per-edge metrics and update edges in place."""
    
    for edge in edges:
        # Persistence score already set from relationship, just normalize
        edge.persistence_score = round(min(edge.persistence_score, 1.0), 4)
        
        # Communication density already computed, just ensure it's normalized
        edge.communication_density = round(min(edge.communication_density, 1.0), 4)


def _compute_graph_metrics(nodes: List[GraphNode], edges: List[GraphEdge]) -> Dict:
    """Compute graph-level metrics (HARDENED with noise suppression)."""
    
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
    n = len(nodes)
    possible_edges = max(1, n * (n - 1))
    graph_density = round(len(edges) / possible_edges, 6)
    
    # Compute average degree
    avg_degree = round(sum(n.node_degree for n in nodes) / len(nodes), 2)
    
    # Compute graph risk score (average of top node risks)
    sorted_nodes = sorted(nodes, key=lambda n: n.risk_score, reverse=True)
    top_risk_nodes = sorted_nodes[:max(1, len(nodes) // 10)]
    graph_risk_score = round(sum(n.risk_score for n in top_risk_nodes) / len(top_risk_nodes), 2)
    
    # FIX 2: Filter high centrality nodes - suppress infrastructure noise
    # Only include non-infrastructure nodes in top rankings
    behavioral_nodes = [n for n in nodes if not is_infrastructure_noise(n) and not is_non_investigative_node(n)]
    sorted_by_centrality = sorted(
        behavioral_nodes,
        key=lambda n: n.centrality_hint,
        reverse=True
    )
    high_centrality_nodes = [n.ip_address for n in sorted_by_centrality[:5]]
    
    # If no behavioral nodes, include some infrastructure for completeness
    if len(high_centrality_nodes) < 3:
        all_sorted = sorted(
            [node for node in nodes if not is_non_investigative_node(node)],
            key=lambda n: n.centrality_hint,
            reverse=True,
        )
        high_centrality_nodes = [n.ip_address for n in all_sorted[:5]]
    
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
