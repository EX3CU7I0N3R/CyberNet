# Layer 4: Graph State - Behavioral Topology Analysis

## Overview

Layer 4 activates graph-state generation, converting host profiles and relationships into a graph-native semantic model for temporal network analysis.

**Architecture:**
```text
Packets
→ Canonical Events
→ Directional Flows
→ Behavioral Metrics
→ Host Profiles + Relationships
→ Graph Nodes + Graph Edges
→ Graph State + Temporal Snapshots    ← Layer 4
→ Exports (NDJSON/CSV/JSON)
```

Layer 4 is **backend-only semantic graph modeling**. It does NOT include:
- Frontend rendering
- React, D3, Cytoscape, Sigma.js
- Databases
- WebSocket servers
- ML/algorithms

## Core Components

### 1. Graph Models (behavior/schemas.py)

#### GraphNode
Represents a host in the behavioral topology.

**Identity:**
- `node_id`: Stable hash of IP address
- `ip_address`: Host IP
- `hostname`: Optional DNS name
- `inferred_role`: Infrastructure device / workstation / server

**Behavior:**
- `risk_score`: 0-100 risk assessment
- `confidence`: 0-1 confidence in assessment
- `behavioral_indicators`: List of risk indicators
- `protocol_diversity`: Count of unique protocols
- `communication_density`: Normalized interaction intensity

**Graph Semantics:**
- `node_degree`: Count of neighbors
- `weighted_degree`: Sum of edge weights
- `centrality_hint`: 0-1 importance in topology
- `node_priority`: Risk × centrality composite

**Temporal:**
- `first_seen`: ISO timestamp
- `last_seen`: ISO timestamp
- `replay_sequence_start`: Packet index at first activity
- `replay_sequence_end`: Packet index at last activity

---

#### GraphEdge
Represents a directed relationship between hosts.

**Identity:**
- `edge_id`: Stable hash of source→target
- `source_node`: Source node ID
- `target_node`: Target node ID

**Relationship Semantics:**
- `relationship_type`: persistent_tls, periodic_dns, dhcp_assignment, suspicious_communication, interaction
- `communication_pattern`: continuous, periodic, bursty, sporadic
- `directionality`: directed (always)

**Behavior:**
- `relationship_risk`: 0-100 risk score
- `persistence_score`: 0-1 relationship stability
- `communication_density`: 0-1 interaction intensity
- `protocol_diversity`: Count of protocols on edge

**Temporal:**
- `first_seen`: ISO timestamp
- `last_seen`: ISO timestamp
- `replay_sequence_start`: Packet index at first interaction
- `replay_sequence_end`: Packet index at last interaction

---

#### GraphState
Complete graph topology snapshot.

**Structure:**
- `snapshot_id`: Unique identifier
- `timestamp`: When this state applies
- `node_count`: Total nodes in graph
- `edge_count`: Total edges in graph
- `graph_density`: actual_edges / possible_edges
- `graph_risk_score`: Average risk of top-10% nodes
- `isolated_node_count`: Nodes with no edges

**Content:**
- `nodes`: List of GraphNode entities
- `edges`: List of GraphEdge entities

**Metrics:**
- `high_centrality_nodes`: Top 5 by importance
- `relationship_types`: Unique edge types present

**Replay Support:**
- `replay_sequence_start`: Min packet index
- `replay_sequence_end`: Max packet index

---

#### TemporalSnapshot
Time-windowed graph state with replay semantics.

**Window:**
- `snapshot_id`: Unique identifier
- `window_start`: ISO timestamp (start of 1-minute window)
- `window_end`: ISO timestamp (end of 1-minute window)

**Content:**
- `node_count`: Nodes active in window
- `edge_count`: Edges active in window
- `active_nodes`: List of IP addresses
- `active_edges`: List of edge IDs

**Graph State:**
- `graph_state`: Full GraphState for this window

**Replay Metadata:**
- `replay_sequence_start`: Min packet index in window
- `replay_sequence_end`: Max packet index in window

---

### 2. Graph Builder (behavior/graph_builder.py)

Converts host profiles and relationships into graph-native entities.

#### build_graph_nodes(host_profiles)
Creates GraphNode from each HostProfile.

**Mapping:**
- `node_id` = sha256("node:{ip_address}")[:16]
- `risk_score` = profile.risk_score
- `behavioral_indicators` = profile.behavioral_indicators
- `protocol_diversity` = count of unique protocols
- `communication_density` = normalized flow count

**Temporal Lineage:**
- `replay_sequence_start` = profile.first_seen_sequence
- `replay_sequence_end` = profile.last_seen_sequence

---

#### build_graph_edges(relationships)
Creates GraphEdge from each HostRelationship.

**Mapping:**
- `edge_id` = relationship.edge_id
- `relationship_type` = inferred from protocols + indicators
- `communication_pattern` = inferred from persistence score

**Type Inference:**
```python
if "persistent_tls_relationship" in indicators:
    return "persistent_tls"
elif "periodic_relationship_activity" in indicators:
    return "periodic_communication"
elif "dns" in protocols:
    return "periodic_dns"
elif "smb" in protocols:
    return "smb_administrative"
else:
    return "interaction"
```

**Pattern Inference:**
```python
if persistence >= 0.7:      return "continuous"
elif persistence >= 0.4:    return "periodic"
elif flows <= 3:            return "sporadic"
else:                       return "bursty"
```

---

#### compute_graph_hashes(nodes, edges)
Computes stable hashes for future diff engine support.

**Returns:**
```python
{
    "node_hashes": {node_id: sha256_hash, ...},
    "edge_hashes": {edge_id: sha256_hash, ...},
    "graph_fingerprint": sha256(all_hashes)
}
```

This enables deterministic comparison across snapshots for the diff engine (Layer 5).

---

### 3. Graph Metrics Engine (behavior/graph_metrics.py)

Lightweight graph analysis. NO expensive algorithms.

#### compute_graph_metrics(nodes, edges)

**Per-Node Metrics:**
- `node_degree` = count of neighbors
- `weighted_degree` = sum of edge weights
- `centrality_hint` = (degree_norm × 0.6) + (risk_signal × 0.4)
- `node_priority` = (risk_score × 0.5) + (centrality × 50)
- `communication_density` = weighted_degree / (node_degree + 1)

**Per-Edge Metrics:**
- `persistence_score` = from relationship (normalized to 0-1)
- `communication_density` = packets / (flows + 1)

**Graph-Level Metrics:**
- `graph_density` = edge_count / (node_count × (node_count - 1))
- `avg_node_degree` = mean of all node degrees
- `graph_risk_score` = mean of top 10% nodes by risk
- `isolated_node_count` = nodes with degree 0
- `high_centrality_nodes` = top 5 by centrality
- `suspicious_edges` = count where risk_score >= 35

---

#### compute_community_detection(nodes, edges)

Simple connectivity clustering (no expensive algorithms).

**Algorithm:**
1. Build adjacency from edges
2. BFS to find connected components
3. Return communities as {community_0: [node_ids], ...}

**Use:**
Lightweight community structure for visualization hints.

---

### 4. Graph State Builder (behavior/graph_state.py)

Builds complete graph states and temporal snapshots.

#### build_graph_state(host_profiles, relationships)

**Process:**
1. Convert profiles → nodes, relationships → edges
2. Compute graph metrics
3. Compute stable hashes
4. Determine temporal boundaries
5. Build GraphState object

**Output:**
Single GraphState representing the full network at a moment in time.

---

#### build_temporal_snapshots(host_profiles, relationships, snapshot_interval_seconds=60)

**Process:**
1. Determine capture start/end from profiles and relationships
2. Slice into time windows (default: 1 minute)
3. For each window:
   - Filter active profiles/relationships
   - Build graph state for that window
   - Collect active nodes/edges
   - Determine replay sequence markers
4. Return list of TemporalSnapshot

**Output:**
List of time-windowed snapshots, each with its own graph state and replay metadata.

---

## Runtime Pipeline

### STEP 6: Building Graph State
```
[*] STEP 6: Building graph state...
    [OK] Built graph with 104 nodes and 201 edges
    [OK] Graph density: 0.018764
    [OK] Graph risk score: 25.6
```

Calls `build_graph_state(host_profiles, relationships)`.

---

### STEP 7: Generating Temporal Snapshots
```
[*] STEP 7: Generating temporal snapshots...
    [OK] Generated 262 temporal snapshots
    [OK] Snapshot time window: 2026-02-28T22:55:06.482909Z to 2026-03-01T03:17:06.482909Z
```

Calls `build_temporal_snapshots(host_profiles, relationships)` with 60-second windows.

---

### STEP 8: Analysis Summary
Existing summary (direction, protocol, suspicious flows, host summary) plus new:

---

#### Graph State Summary
```
================================================================================
GRAPH STATE SUMMARY
================================================================================

    Graph Nodes: 104
    Graph Edges: 201
    Graph Density: 0.018764
    Graph Risk Score: 25.6
    Isolated Nodes: 0

    High Centrality Nodes:
      - 10.2.28.88
      - 0.0.0.0
      - 10.2.28.1
      - 10.2.28.2
      - 10.2.28.255

    Relationship Types:
      - dhcp_assignment
      - interaction
      - periodic_dns
      - persistent_tls

    Temporal Snapshots: 262 generated
    Average Node Degree: 1.99
    Suspicious Edges: 6
    Network Communities: 1 detected

    Replay Metadata:
      - Deterministic replay ordering enabled
      - Sequence start: 2
      - Sequence end: 15511
```

---

### STEP 9: Exporting Graph Artifacts

**New NDJSON Exports:**
- `graph_nodes.ndjson`: All GraphNode entities (1 per line)
- `graph_edges.ndjson`: All GraphEdge entities (1 per line)
- `graph_snapshots.ndjson`: All TemporalSnapshot entities (1 per line)
- `graph_state.ndjson`: Single GraphState entity

**Properties:**
- JSON Lines format (NDJSON)
- Replay-safe (deterministic ordering)
- Frontend-ready (all fields included)
- Stream-safe (one entity per line)
- WebSocket-ready (can be sent incrementally)

---

## Data Flow Examples

### Example 1: From Host Profile to Graph Node

**Input (HostProfile):**
```python
HostProfile(
    ip_address="10.2.28.88",
    risk_score=74.0,
    behavioral_indicators=["unusual_external_persistence"],
    protocol_diversity=5,
    first_seen_sequence=100,
    last_seen_sequence=15000
)
```

**Output (GraphNode):**
```python
GraphNode(
    node_id="8a9f1c2d3e4f5a6b",
    ip_address="10.2.28.88",
    inferred_role="unknown",
    risk_score=74.0,
    confidence=0.746,
    behavioral_indicators=["unusual_external_persistence"],
    protocol_diversity=5,
    communication_density=0.45,
    node_degree=0,  # Will be updated by metrics engine
    weighted_degree=0.0,
    centrality_hint=0.0,
    node_priority=0.0,
    first_seen="2026-02-28T22:55:00Z",
    last_seen="2026-03-01T03:15:00Z",
    replay_sequence_start=100,
    replay_sequence_end=15000,
    metadata={...}
)
```

---

### Example 2: From Relationship to Graph Edge

**Input (HostRelationship):**
```python
HostRelationship(
    edge_id="dc6321571d91d0fe",
    source="10.2.28.88",
    target="45.131.214.85",
    relationship_risk=68.1,
    persistence=0.45,
    protocols=["https"],
    relationship_indicators=["persistent_tls_relationship"]
)
```

**Output (GraphEdge):**
```python
GraphEdge(
    edge_id="dc6321571d91d0fe",
    source_node="8a9f1c2d3e4f5a6b",
    target_node="5c7e3b1a9f2d4c6e",
    relationship_type="persistent_tls",
    communication_pattern="periodic",
    directionality="directed",
    relationship_risk=68.1,
    persistence_score=0.45,
    communication_density=0.32,
    protocol_diversity=1,
    first_seen="2026-02-28T22:55:00Z",
    last_seen="2026-03-01T03:15:00Z",
    replay_sequence_start=100,
    replay_sequence_end=15000,
    metadata={...}
)
```

---

### Example 3: Temporal Snapshot Window

**Window: 22:55:00 – 22:56:00**

**Active Profiles:** 32
**Active Relationships:** 57

**Output (TemporalSnapshot):**
```python
TemporalSnapshot(
    snapshot_id="7ca03b57d65c2e3b",
    window_start="2026-02-28T22:55:06.482909Z",
    window_end="2026-02-28T22:56:06.482909Z",
    node_count=32,
    edge_count=57,
    active_nodes=["0.0.0.0", "10.2.28.1", "10.2.28.2", ...],
    active_edges=["edge_1", "edge_2", ...],
    graph_state=GraphState(...),
    replay_sequence_start=2,
    replay_sequence_end=15511,
    metadata={"profile_count": 32, "relationship_count": 57}
)
```

---

## Replay Safety Guarantees

Layer 4 preserves deterministic replay ordering:

1. **Packet-Level Ordering:** `replay_sequence_id` from original packet index
2. **Timeline-Index Ordering:** Chronological ordering across packets
3. **Node Lineage:** `replay_sequence_start` and `replay_sequence_end` preserve sequence range
4. **Edge Lineage:** Same replay sequence markers on edges
5. **Snapshot Windows:** Each snapshot has replay markers for its time range
6. **Stable Hashing:** Node/edge hashes deterministic across runs

**Implication:**
Graph can be replayed deterministically:
1. Load packets in `replay_sequence_id` order
2. Build events with `timeline_index` ordering
3. Construct graph nodes/edges with sequence markers
4. Reconstruct temporal snapshots window-by-window
5. Result is byte-identical to original run

---

## Future Layer 5: Diff Engine

Layer 4 prepares for Layer 5 (temporal diff engine) with:

1. **Stable Node Hashes:**
   - Node hashes deterministic from identity + risk + indicators
   - Enables node emergence detection

2. **Stable Edge Hashes:**
   - Edge hashes deterministic from source + target + risk
   - Enables relationship emergence detection

3. **Graph Fingerprints:**
   - Graph-wide hash enables snapshot diffing
   - Detects topology evolution

4. **Snapshot Lineage:**
   - Temporal snapshots linked by time windows
   - Enables frame-by-frame diff analysis

5. **Replay Sequence Markers:**
   - Each entity marked with start/end sequence
   - Enables deterministic frame reconstruction

---

## Constraints & Design Decisions

### Lightweight Metrics (By Design)

**Why:**
- Real-time analysis on captured traffic
- No expensive graph algorithms
- Replay-safe (deterministic, no randomness)

**What's NOT Included:**
- PageRank / eigenvector centrality
- K-core decomposition
- Louvain clustering
- Graph convolutions
- ML inference

---

### No Persistence Layer

**Why:**
- Backend semantic modeling only
- Exports provide persistence
- No database dependency

**How to Persist:**
- Load NDJSON exports into target system (Neo4j, etc.)
- Implement custom loader for your backend

---

### No Frontend Rendering

**Why:**
- Backend analysis layer only
- Exports prepare data for rendering

**How to Render:**
- Use exported NDJSON with Cytoscape.js
- Use exported JSON with D3.js
- Use exported format with custom visualization

---

## Integration Points

### With Existing Layers
- Inputs: `host_profiles` and `relationships` from Layer 3
- Outputs: `graph_nodes`, `graph_edges`, `graph_state`, `temporal_snapshots`

### With Layer 5 (Diff Engine)
- Stable hashes enable snapshot comparison
- Replay sequences enable deterministic reconstruction
- Community detection prepares for topology evolution analysis

### With Frontend Systems
- NDJSON exports are stream-safe
- JSON fields are frontend-ready
- All data is serialized (no Python objects)

---

## File Structure

```
behavior/
  schemas.py              ← GraphNode, GraphEdge, GraphState, TemporalSnapshot
  graph_builder.py        ← build_graph_nodes, build_graph_edges, compute_graph_hashes
  graph_metrics.py        ← compute_graph_metrics, compute_community_detection
  graph_state.py          ← build_graph_state, build_temporal_snapshots
  
main.py                   ← STEPS 6-9 integration
```

---

## Performance Characteristics

For sample.pcap (15,512 packets, 1,140 flows, 104 hosts, 201 relationships):

- Graph state generation: < 1 second
- Temporal snapshots (262 windows): < 5 seconds
- Graph metrics: < 100ms
- Total Layer 4 runtime: < 10 seconds

**Memory footprint:**
- 104 nodes + 201 edges + 262 snapshots ≈ 50MB in-memory

---

## Debugging & Troubleshooting

### Missing Replay Metadata
Check that host profiles have `first_seen_sequence` and `last_seen_sequence` set.

### Empty Temporal Snapshots
Verify that profiles/relationships have valid ISO timestamps.

### Node Degree = 0
Check that edges reference correct node IDs.

### Graph Density Issues
Verify node_count > 0 and edge_count > 0.

---

## Next Steps (Layer 5)

Layer 5 will implement the diff engine:

1. **Snapshot Diffing:** Compare consecutive snapshots
2. **Node Emergence:** Detect new hosts appearing
3. **Edge Emergence:** Detect new relationships forming
4. **Risk Escalation:** Track risk score changes
5. **Topology Evolution:** Identify structural changes
6. **Replay-Based Diffing:** Frame-by-frame analysis

All enabled by Layer 4's stable hashing and replay semantics.
