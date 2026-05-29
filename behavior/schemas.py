from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HostProfile(BaseModel):
    ip_address: str
    mac_address: Optional[str] = None
    hostname: Optional[str] = None
    user_identity: Optional[str] = None

    flow_count: int = 0
    external_flow_count: int = 0
    internal_flow_count: int = 0
    initiated_flow_count: int = 0
    responded_flow_count: int = 0
    packet_count: int = 0
    total_bytes: int = 0
    upload_bytes: int = 0
    download_bytes: int = 0
    upload_download_ratio: float = 0.0
    average_flow_duration: float = 0.0

    external_connections: int = 0
    external_unique_hosts: int = 0
    external_unique_relationships: int = 0
    internal_connections: int = 0
    internal_unique_hosts: int = 0
    internal_unique_relationships: int = 0
    inbound_connections: int = 0
    outbound_connections: int = 0
    unique_destinations: int = 0
    unique_peers: int = 0
    unique_ports: int = 0
    protocol_relationships: int = 0
    persistent_relationships: int = 0
    protocols: List[str] = Field(default_factory=list)
    transports: List[str] = Field(default_factory=list)
    protocol_diversity: int = 0
    transport_diversity: int = 0
    unknown_protocol_ratio: float = 0.0
    encrypted_flow_ratio: float = 0.0
    protocol_confidence_avg: float = 0.0
    telemetry_completeness: float = 0.0
    outbound_ratio: float = 0.0
    inbound_ratio: float = 0.0
    internal_ratio: float = 0.0

    beacon_flow_count: int = 0
    suspicious_flow_count: int = 0
    suppressed_flow_count: int = 0
    persistent_connection_count: int = 0
    long_lived_flow_count: int = 0
    periodic_flow_ratio: float = 0.0
    persistent_connection_ratio: float = 0.0

    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    first_seen_sequence: int = 0
    last_seen_sequence: int = 0
    first_timeline_index: int = 0
    last_timeline_index: int = 0
    active_duration: float = 0.0
    activity_density: float = 0.0
    session_density: float = 0.0
    activity_cluster_count: int = 0
    active_time_buckets: List[str] = Field(default_factory=list)
    hourly_activity_distribution: Dict[str, int] = Field(default_factory=dict)

    inferred_role: str = "unknown"
    role_confidence: float = 0.0
    role_evidence: List[str] = Field(default_factory=list)

    graph_weight: float = 0.0
    graph_degree: int = 0
    graph_importance: float = 0.0
    graph_node_size: float = 8.0
    graph_risk_color: str = "#7aa6c2"
    graph_cluster_group: str = "internal_host"
    graph_node_type: str = "host"
    graph_node: Dict = Field(default_factory=dict)
    edge_hints: List[Dict] = Field(default_factory=list)

    risk_score: float = 0.0
    confidence: float = 0.0
    severity: str = "informational"
    behavioral_indicators: List[str] = Field(default_factory=list)
    indicator_details: Dict[str, float] = Field(default_factory=dict)
    baseline_state: Dict = Field(default_factory=dict)

    @property
    def host(self) -> str:
        return self.ip_address


class HostBaselineSnapshot(BaseModel):
    snapshot_id: str
    generated_at: str
    host_count: int
    hosts: Dict[str, Dict]


class HostGraphNode(BaseModel):
    id: str
    risk_score: float
    confidence: float
    connections: int
    protocols: List[str]
    node_size: float
    node_color: str
    cluster_group: str
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    metadata: Dict = Field(default_factory=dict)


class HostRelationship(BaseModel):
    edge_id: str
    source: str
    target: str
    relationship_risk: float = 0.0
    confidence: float = 0.0
    severity: str = "informational"
    flows: int = 0
    packet_count: int = 0
    total_bytes: int = 0
    protocols: List[str] = Field(default_factory=list)
    transports: List[str] = Field(default_factory=list)
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    first_seen_sequence: int = 0
    last_seen_sequence: int = 0
    persistence: float = 0.0
    temporal_buckets: List[str] = Field(default_factory=list)
    protocol_diversity: int = 0
    directionality: str = "directed"
    relationship_indicators: List[str] = Field(default_factory=list)
    graph_weight: float = 0.0
    graph_edge_color: str = "#7aa6c2"
    graph_edge_width: float = 1.0
    metadata: Dict = Field(default_factory=dict)


# ================================================================================
# Layer 4: Graph State Models
# ================================================================================


class GraphNode(BaseModel):
    """Graph-native node entity representing a host in the behavioral topology."""
    
    # Identity
    node_id: str
    ip_address: str
    hostname: Optional[str] = None
    inferred_role: str = "unknown"
    
    # Behavior
    risk_score: float = 0.0
    confidence: float = 0.0
    behavioral_indicators: List[str] = Field(default_factory=list)
    protocol_diversity: int = 0
    communication_density: float = 0.0
    
    # Graph semantics
    node_degree: int = 0
    weighted_degree: float = 0.0
    centrality_hint: float = 0.0
    node_priority: float = 0.0
    
    # Temporal
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    replay_sequence_start: int = 0
    replay_sequence_end: int = 0
    
    # Metadata
    metadata: Dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Graph-native edge entity representing a relationship in the behavioral topology."""
    
    # Identity
    edge_id: str
    source_node: str
    target_node: str
    
    # Relationship semantics
    relationship_type: str = "interaction"
    communication_pattern: str = "continuous"
    directionality: str = "directed"
    
    # Behavior
    relationship_risk: float = 0.0
    persistence_score: float = 0.0
    communication_density: float = 0.0
    protocol_diversity: int = 0
    
    # Temporal
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    replay_sequence_start: int = 0
    replay_sequence_end: int = 0
    
    # Metadata
    metadata: Dict = Field(default_factory=dict)


class GraphState(BaseModel):
    """Graph state representing behavioral topology at a moment in time."""
    
    snapshot_id: str
    timestamp: str
    node_count: int = 0
    edge_count: int = 0
    graph_density: float = 0.0
    graph_risk_score: float = 0.0
    isolated_node_count: int = 0
    
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    
    # Metrics
    high_centrality_nodes: List[str] = Field(default_factory=list)
    relationship_types: List[str] = Field(default_factory=list)
    
    # Replay support
    replay_sequence_start: int = 0
    replay_sequence_end: int = 0
    
    # Metadata
    metadata: Dict = Field(default_factory=dict)


class TemporalSnapshot(BaseModel):
    """Time-windowed graph snapshot with replay semantics."""
    
    snapshot_id: str
    window_start: str
    window_end: str
    
    node_count: int = 0
    edge_count: int = 0
    
    active_nodes: List[str] = Field(default_factory=list)
    active_edges: List[str] = Field(default_factory=list)
    
    graph_state: GraphState = Field(default_factory=lambda: GraphState(
        snapshot_id="",
        timestamp="",
        nodes=[],
        edges=[]
    ))
    
    # Replay metadata
    replay_sequence_start: int = 0
    replay_sequence_end: int = 0
    
    # Metadata
    metadata: Dict = Field(default_factory=dict)
