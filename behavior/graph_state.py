"""
Layer 4: Graph State Builder
Builds graph state objects and temporal snapshots with replay semantics.
"""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Dict, List

from behavior.graph_builder import build_graph_edges, build_graph_nodes, compute_graph_hashes
from behavior.graph_metrics import compute_community_detection, compute_graph_metrics
from behavior.schemas import (
    GraphEdge,
    GraphNode,
    GraphState,
    HostProfile,
    HostRelationship,
    TemporalSnapshot,
)


def build_graph_state(
    host_profiles: List[HostProfile],
    relationships: List[HostRelationship]
) -> GraphState:
    """
    Build a complete graph state from host profiles and relationships.
    
    This represents the behavioral topology at a moment in time.
    Includes nodes, edges, metrics, and replay metadata.
    """
    # Build graph entities
    nodes = build_graph_nodes(host_profiles)
    edges = build_graph_edges(relationships)
    
    # Compute metrics
    graph_metrics = compute_graph_metrics(nodes, edges)
    
    # Compute stable hashes for future diff engine
    hashes = compute_graph_hashes(nodes, edges)
    
    # Determine temporal boundaries from nodes and edges
    first_sequences = [n.replay_sequence_start for n in nodes if n.replay_sequence_start > 0]
    last_sequences = [n.replay_sequence_end for n in nodes if n.replay_sequence_end > 0]
    first_seen_dates = [n.first_seen for n in nodes if n.first_seen]
    last_seen_dates = [n.last_seen for n in nodes if n.last_seen]
    
    replay_sequence_start = min(first_sequences) if first_sequences else 0
    replay_sequence_end = max(last_sequences) if last_sequences else 0
    
    # Compute snapshot timestamp (latest activity)
    if last_seen_dates:
        latest_timestamp = max(_parse_timestamp(ts) for ts in last_seen_dates)
        timestamp_str = latest_timestamp.isoformat().replace("+00:00", "Z")
    else:
        timestamp_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Create snapshot ID
    snapshot_id = _compute_snapshot_id(nodes, edges)
    
    # Build graph state
    graph_state = GraphState(
        snapshot_id=snapshot_id,
        timestamp=timestamp_str,
        node_count=graph_metrics["node_count"],
        edge_count=graph_metrics["edge_count"],
        graph_density=graph_metrics["graph_density"],
        graph_risk_score=graph_metrics["graph_risk_score"],
        isolated_node_count=graph_metrics["isolated_node_count"],
        
        nodes=nodes,
        edges=edges,
        
        high_centrality_nodes=graph_metrics["high_centrality_nodes"],
        relationship_types=graph_metrics["relationship_types"],
        
        replay_sequence_start=replay_sequence_start,
        replay_sequence_end=replay_sequence_end,
        
        metadata={
            "graph_fingerprint": hashes["graph_fingerprint"],
            "avg_node_degree": graph_metrics["avg_node_degree"],
            "suspicious_edges": graph_metrics["suspicious_edges"],
            "communities": compute_community_detection(nodes, edges),
        }
    )
    
    return graph_state


def build_temporal_snapshots(
    host_profiles: List[HostProfile],
    relationships: List[HostRelationship],
    snapshot_interval_seconds: int = 60
) -> List[TemporalSnapshot]:
    """
    Build time-windowed graph snapshots with replay semantics.
    
    Slices telemetry into temporal windows and generates a snapshot for each.
    
    Args:
        host_profiles: List of host profiles
        relationships: List of relationships
        snapshot_interval_seconds: Size of time window in seconds (default: 60)
    
    Returns:
        List of TemporalSnapshot objects
    """
    # Determine temporal boundaries
    first_seen_dates = [
        _parse_timestamp(ts) for ts in
        [p.first_seen for p in host_profiles if p.first_seen] +
        [r.first_seen for r in relationships if r.first_seen]
    ]
    last_seen_dates = [
        _parse_timestamp(ts) for ts in
        [p.last_seen for p in host_profiles if p.last_seen] +
        [r.last_seen for r in relationships if r.last_seen]
    ]
    
    if not first_seen_dates or not last_seen_dates:
        return []
    
    capture_start = min(first_seen_dates)
    capture_end = max(last_seen_dates)
    
    # Generate snapshot windows
    snapshots = []
    current_window_start = capture_start
    
    while current_window_start < capture_end:
        current_window_end = current_window_start + timedelta(seconds=snapshot_interval_seconds)
        
        # Filter entities active in this window
        active_profiles = _filter_profiles_by_window(
            host_profiles,
            current_window_start,
            current_window_end
        )
        active_relationships = _filter_relationships_by_window(
            relationships,
            current_window_start,
            current_window_end
        )
        
        if active_profiles or active_relationships:
            # Build snapshot for this window
            snapshot = _build_snapshot_for_window(
                active_profiles,
                active_relationships,
                current_window_start,
                current_window_end
            )
            snapshots.append(snapshot)
        
        current_window_start = current_window_end
    
    return snapshots


def _build_snapshot_for_window(
    profiles: List[HostProfile],
    relationships: List[HostRelationship],
    window_start: datetime,
    window_end: datetime
) -> TemporalSnapshot:
    """Build a single temporal snapshot for a time window."""
    
    # Build graph state for this window
    graph_state = build_graph_state(profiles, relationships)
    
    # Collect active node and edge IDs
    active_nodes = [n.ip_address for n in graph_state.nodes]
    active_edges = [e.edge_id for e in graph_state.edges]
    
    # Determine replay sequence boundaries for this window
    replay_starts = [p.first_seen_sequence for p in profiles if p.first_seen_sequence > 0]
    replay_ends = [p.last_seen_sequence for p in profiles if p.last_seen_sequence > 0]
    
    replay_sequence_start = min(replay_starts) if replay_starts else 0
    replay_sequence_end = max(replay_ends) if replay_ends else 0
    
    # Create snapshot ID
    snapshot_id = _compute_temporal_snapshot_id(
        window_start,
        window_end,
        len(profiles),
        len(relationships)
    )
    
    # Format timestamps
    window_start_str = window_start.isoformat().replace("+00:00", "Z")
    window_end_str = window_end.isoformat().replace("+00:00", "Z")
    
    snapshot = TemporalSnapshot(
        snapshot_id=snapshot_id,
        window_start=window_start_str,
        window_end=window_end_str,
        
        node_count=graph_state.node_count,
        edge_count=graph_state.edge_count,
        
        active_nodes=active_nodes,
        active_edges=active_edges,
        
        graph_state=graph_state,
        
        replay_sequence_start=replay_sequence_start,
        replay_sequence_end=replay_sequence_end,
        
        metadata={
            "profile_count": len(profiles),
            "relationship_count": len(relationships),
            "window_duration_seconds": (window_end - window_start).total_seconds(),
        }
    )
    
    return snapshot


def _filter_profiles_by_window(
    profiles: List[HostProfile],
    window_start: datetime,
    window_end: datetime
) -> List[HostProfile]:
    """Filter host profiles that are active in the given time window."""
    active = []
    
    for profile in profiles:
        if not profile.first_seen or not profile.last_seen:
            continue
        
        profile_start = _parse_timestamp(profile.first_seen)
        profile_end = _parse_timestamp(profile.last_seen)
        
        # Check for overlap with window
        if profile_end >= window_start and profile_start <= window_end:
            active.append(profile)
    
    return active


def _filter_relationships_by_window(
    relationships: List[HostRelationship],
    window_start: datetime,
    window_end: datetime
) -> List[HostRelationship]:
    """Filter relationships that are active in the given time window."""
    active = []
    
    for relationship in relationships:
        if not relationship.first_seen or not relationship.last_seen:
            continue
        
        rel_start = _parse_timestamp(relationship.first_seen)
        rel_end = _parse_timestamp(relationship.last_seen)
        
        # Check for overlap with window
        if rel_end >= window_start and rel_start <= window_end:
            active.append(relationship)
    
    return active


def _parse_timestamp(timestamp: str) -> datetime:
    """Parse ISO timestamp string to UTC datetime."""
    parsed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _compute_snapshot_id(nodes: List[GraphNode], edges: List[GraphEdge]) -> str:
    """Compute stable snapshot ID from nodes and edges."""
    node_ids = "|".join(sorted(n.node_id for n in nodes))
    edge_ids = "|".join(sorted(e.edge_id for e in edges))
    content = f"{node_ids}:{edge_ids}"
    return sha256(content.encode()).hexdigest()[:16]


def _compute_temporal_snapshot_id(
    window_start: datetime,
    window_end: datetime,
    node_count: int,
    edge_count: int
) -> str:
    """Compute stable temporal snapshot ID from window and counts."""
    content = f"{window_start.isoformat()}:{window_end.isoformat()}:{node_count}:{edge_count}"
    return sha256(content.encode()).hexdigest()[:16]
