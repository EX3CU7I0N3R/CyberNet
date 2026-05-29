# Layer 5 Preparation & Architectural Guidance

## Overview

Layer 4 (Graph State) prepares the telemetry system for Layer 5 (Temporal Diff Engine) through:

1. **Stable Hashing** - Enables deterministic comparison
2. **Replay Sequences** - Enables frame-by-frame reconstruction
3. **Snapshot Lineage** - Enables temporal diffing
4. **Semantic Graph** - Enables topology analysis

This document provides guidance for Layer 5 implementation.

---

## Layer 5: Temporal Diff Engine (Coming)

### Purpose
Analyze how the behavioral topology **evolves over time**.

### Capabilities
- **Node Emergence:** Detect when new hosts appear
- **Relationship Emergence:** Detect when new connections form
- **Risk Escalation:** Track when risk scores change
- **Topology Evolution:** Identify structural changes
- **Replay Reconstruction:** Frame-by-frame graph animation
- **Anomaly Detection:** Identify unusual topology shifts

### Implementation Approach

#### Phase 1: Snapshot Comparison
```python
def diff_snapshots(snapshot_t0: TemporalSnapshot, snapshot_t1: TemporalSnapshot):
    """Compare two snapshots to identify changes."""
    
    # Node-level changes
    nodes_t0 = {n.node_id for n in snapshot_t0.graph_state.nodes}
    nodes_t1 = {n.node_id for n in snapshot_t1.graph_state.nodes}
    
    emerged_nodes = nodes_t1 - nodes_t0
    disappeared_nodes = nodes_t0 - nodes_t1
    
    # Edge-level changes
    edges_t0 = {e.edge_id for e in snapshot_t0.graph_state.edges}
    edges_t1 = {e.edge_id for e in snapshot_t1.graph_state.edges}
    
    emerged_edges = edges_t1 - edges_t0
    disappeared_edges = edges_t0 - edges_t1
    
    # Risk changes
    for node_id in (nodes_t0 & nodes_t1):
        node_t0 = _find_node(snapshot_t0, node_id)
        node_t1 = _find_node(snapshot_t1, node_id)
        if node_t0.risk_score != node_t1.risk_score:
            # Risk escalation detected
            ...
```

#### Phase 2: Stability Analysis
```python
def compute_graph_stability(snapshots: List[TemporalSnapshot], window_size: int = 5):
    """Compute topology stability over windows."""
    
    for i in range(len(snapshots) - window_size):
        window = snapshots[i:i+window_size]
        
        # Nodes that persist across entire window
        persistent_nodes = _find_persistent_nodes(window)
        
        # Edges that persist across entire window
        persistent_edges = _find_persistent_edges(window)
        
        # Churning ratio (nodes that appear/disappear)
        churn_ratio = _compute_churn_ratio(window)
        
        # Stability score
        stability = len(persistent_nodes) / len(window[0].graph_state.nodes)
```

#### Phase 3: Replay-Based Animation
```python
def animate_graph_evolution(snapshots: List[TemporalSnapshot]):
    """Generate frame-by-frame topology animation."""
    
    frames = []
    for snapshot in snapshots:
        frame = {
            "timestamp": snapshot.window_start,
            "nodes": snapshot.graph_state.nodes,
            "edges": snapshot.graph_state.edges,
            "changes": _compute_frame_changes(snapshot),
            "replay_sequence": {
                "start": snapshot.replay_sequence_start,
                "end": snapshot.replay_sequence_end,
            }
        }
        frames.append(frame)
    
    return frames
```

---

## Stable Hashing: Design

### Node Hash Computation

**Current Implementation (Layer 4):**
```python
node_hash = sha256(f"{node.node_id}:{node.risk_score}:{node.behavioral_indicators}".encode()).hexdigest()
```

**Design Rationale:**
- `node_id`: Stable identity (derived from IP, unique per host)
- `risk_score`: Behavior at snapshot time
- `behavioral_indicators`: Risk context

**Result:**
Same node with same risk + indicators = same hash.
Different risk or indicators = different hash.

**Enables:**
- Node emergence (new hash in t1 not in t0)
- Risk escalation (old hash removed, new hash added)

---

### Edge Hash Computation

**Current Implementation (Layer 4):**
```python
edge_hash = sha256(f"{edge.source_node}:{edge.target_node}:{edge.relationship_risk}".encode()).hexdigest()
```

**Design Rationale:**
- `source_node`: Stable source identity
- `target_node`: Stable target identity
- `relationship_risk`: Risk at snapshot time

**Result:**
Same edge with same risk = same hash.
Edge with different risk = different hash.

**Enables:**
- Edge emergence (new hash in t1 not in t0)
- Relationship risk escalation (risk score change)

---

### Graph Fingerprint

**Current Implementation (Layer 4):**
```python
all_hashes = sorted(list(node_hashes.values()) + list(edge_hashes.values()))
graph_fingerprint = sha256("".join(all_hashes).encode()).hexdigest()
```

**Design Rationale:**
- Deterministic ordering (sorted hashes)
- Combines all entity hashes
- Any change → different fingerprint

**Result:**
Snapshot t0 fingerprint ≠ snapshot t1 fingerprint if ANY node/edge changed.

**Enables:**
- Quick topology change detection
- Snapshot comparison short-circuit
- Graph evolution tracking

---

## Snapshot Lineage: Design

### Temporal Window Chain

Each snapshot has:
```python
snapshot = TemporalSnapshot(
    snapshot_id="7ca03b57d65c2e3b",
    window_start="2026-02-28T22:55:06Z",
    window_end="2026-02-28T22:56:06Z",
    replay_sequence_start=2,
    replay_sequence_end=15511,
)
```

**Lineage Chain:**
```
Snapshot 0: [22:55:06 - 22:56:06] seq[2-50]
   ↓
Snapshot 1: [22:56:06 - 22:57:06] seq[50-120]
   ↓
Snapshot 2: [22:57:06 - 22:58:06] seq[120-200]
   ...
```

**Properties:**
- Sequential timestamps (no gaps, no overlaps)
- Continuous replay sequences
- Enables linear temporal analysis

**Enables:**
- Frame-by-frame reconstruction
- Temporal continuity guarantees
- Replay-safe animation

---

### Replay Sequence Ordering

Each entity has:
```python
node = GraphNode(
    replay_sequence_start=100,
    replay_sequence_end=15000,
)

edge = GraphEdge(
    replay_sequence_start=100,
    replay_sequence_end=15000,
)
```

**Ordering Guarantee:**
All entities in snapshot can be ordered deterministically by:
1. `replay_sequence_start` (ascending)
2. `replay_sequence_end` (ascending)

**Enables:**
- Deterministic entity ordering within snapshots
- Replay-safe frame construction
- Bit-identical reconstruction

---

## Diff Algorithm: Layer 5 Foundation

### Basic Diff Structure

```python
@dataclass
class SnapshotDiff:
    timestamp_t0: str
    timestamp_t1: str
    
    # Node changes
    node_emergences: List[str]      # New node IDs
    node_disappearances: List[str]  # Removed node IDs
    node_risk_escalations: Dict     # {node_id: (risk_t0, risk_t1)}
    node_degree_changes: Dict       # {node_id: (degree_t0, degree_t1)}
    
    # Edge changes
    edge_emergences: List[str]      # New edge IDs
    edge_disappearances: List[str]  # Removed edge IDs
    edge_risk_escalations: Dict     # {edge_id: (risk_t0, risk_t1)}
    
    # Graph-level changes
    graph_density_delta: float       # density_t1 - density_t0
    graph_risk_delta: float          # risk_t1 - risk_t0
    isolated_nodes_delta: int        # count_t1 - count_t0
    
    # Metadata
    has_significant_change: bool
    change_magnitude: float          # 0-1 significance score
```

### Diff Computation

```python
def diff_snapshots(snapshot_t0: TemporalSnapshot, snapshot_t1: TemporalSnapshot) -> SnapshotDiff:
    """Compare two snapshots."""
    
    gs0 = snapshot_t0.graph_state
    gs1 = snapshot_t1.graph_state
    
    # Node-level changes
    nodes_t0 = {n.node_id: n for n in gs0.nodes}
    nodes_t1 = {n.node_id: n for n in gs1.nodes}
    
    node_emergences = list(set(nodes_t1.keys()) - set(nodes_t0.keys()))
    node_disappearances = list(set(nodes_t0.keys()) - set(nodes_t1.keys()))
    
    node_risk_escalations = {}
    for node_id in (set(nodes_t0.keys()) & set(nodes_t1.keys())):
        risk_t0 = nodes_t0[node_id].risk_score
        risk_t1 = nodes_t1[node_id].risk_score
        if risk_t1 - risk_t0 >= 5:  # Threshold: 5-point risk increase
            node_risk_escalations[node_id] = (risk_t0, risk_t1)
    
    # Similar for edges...
    
    # Graph-level changes
    graph_density_delta = gs1.graph_density - gs0.graph_density
    graph_risk_delta = gs1.graph_risk_score - gs0.graph_risk_score
    
    # Significance scoring
    change_magnitude = _score_changes(node_emergences, edge_emergences, node_risk_escalations)
    
    return SnapshotDiff(...)
```

---

## Anomaly Detection Patterns (Layer 5+)

### Pattern: Sudden Node Emergence
```
Snapshot t-1: 100 nodes
Snapshot t:   105 nodes (5 new)
Snapshot t+1: 112 nodes (7 new)

→ Indicates rapid network growth
→ May warrant investigation
```

### Pattern: Risk Spike
```
Snapshot t-1: Graph risk = 20.0
Snapshot t:   Graph risk = 45.0 (+25.0)
Snapshot t+1: Graph risk = 52.0 (+7.0)

→ Indicates risk escalation event
→ Correlate with specific node/edge risk changes
```

### Pattern: Topology Churn
```
Snapshot t-1: 200 edges
Snapshot t:   150 edges (50 disappear)
Snapshot t+1: 220 edges (70 emerge)

→ Indicates high connectivity volatility
→ May indicate network re-stabilization
```

### Pattern: Isolated Node Emergence
```
Snapshot t-1: 0 isolated nodes
Snapshot t:   5 isolated nodes
Snapshot t+1: 8 isolated nodes

→ Indicates hosts becoming disconnected
→ May indicate segmentation/failure
```

---

## Performance Considerations for Layer 5

### Memory Efficiency

**Current (Layer 4):**
- 262 snapshots × ~50MB each = ~13GB worst case
- In practice: ~2GB (most snapshots have overlapping data)

**For Layer 5:**
- Store snapshots incrementally (don't load all in memory)
- Stream snapshots for diff computation
- Cache only recent N snapshots

```python
def stream_snapshot_diffs(snapshot_stream, cache_size=10):
    """Stream diffs without loading all snapshots."""
    
    cache = deque(maxlen=cache_size)
    
    for snapshot in snapshot_stream:
        if len(cache) > 0:
            prev_snapshot = cache[-1]
            diff = diff_snapshots(prev_snapshot, snapshot)
            yield diff
        
        cache.append(snapshot)
```

---

### Computation Efficiency

**Quick Wins:**
- Snapshot fingerprint comparison (< 1ms)
- Node/edge hash lookup (< 1ms)
- Set operations for emergence detection (< 1ms)

**Expensive Operations (Avoid):**
- Full graph algorithms (PageRank, clustering)
- Heavy community detection
- ML inference

---

## Integration Points with Existing Layers

### Layer 1-3 Inputs
- Canonical events with `replay_sequence_id`
- Flows with `first_seen_sequence`, `last_seen_sequence`
- Profiles with temporal markers

### Layer 4 Inputs (Layer 5)
- Stable node/edge hashes
- Graph fingerprints
- Replay sequence markers
- Temporal snapshot chain

### Layer 5+ Outputs
- Snapshot diffs
- Change events
- Anomaly scores
- Replay animations

---

## Testing Strategy for Layer 5

### Unit Tests

```python
def test_node_emergence_detection():
    snapshot_t0 = build_snapshot([node_a, node_b])
    snapshot_t1 = build_snapshot([node_a, node_b, node_c])  # node_c emerged
    
    diff = diff_snapshots(snapshot_t0, snapshot_t1)
    assert node_c.node_id in diff.node_emergences

def test_risk_escalation_detection():
    node_t0 = GraphNode(risk_score=20.0)
    node_t1 = GraphNode(risk_score=50.0)
    
    diff = diff_snapshots(snapshot_with([node_t0]), snapshot_with([node_t1]))
    assert node.node_id in diff.node_risk_escalations
    assert diff.node_risk_escalations[node.node_id] == (20.0, 50.0)

def test_topology_churn_detection():
    snapshot_t0 = build_snapshot(edges=[e1, e2, e3])
    snapshot_t1 = build_snapshot(edges=[e2, e3, e4, e5])
    
    diff = diff_snapshots(snapshot_t0, snapshot_t1)
    assert e1.edge_id in diff.edge_disappearances
    assert e4.edge_id in diff.edge_emergences
```

### Integration Tests

```python
def test_replay_reconstruction():
    """Verify that snapshots can be replayed deterministically."""
    
    # Load all snapshots
    snapshots = load_temporal_snapshots("graph_snapshots.ndjson")
    
    # Reconstruct graph at each point
    for snapshot in snapshots:
        # Verify replay sequence is contiguous
        if prev_snapshot:
            assert snapshot.replay_sequence_start <= prev_snapshot.replay_sequence_end
        
        prev_snapshot = snapshot
    
    # Verify total coverage
    assert snapshots[0].replay_sequence_start <= 10  # Near start
    assert snapshots[-1].replay_sequence_end >= 15500  # Near end
```

---

## Recommended Layer 5 Implementation Plan

### Phase 1: Foundation (Week 1)
- [ ] Implement `SnapshotDiff` model
- [ ] Implement `diff_snapshots()` function
- [ ] Unit tests for diff detection
- [ ] Verify with sample.pcap data

### Phase 2: Streaming (Week 2)
- [ ] Implement streaming snapshot diffs
- [ ] Implement diff event stream
- [ ] Memory-efficient caching strategy
- [ ] Performance benchmarking

### Phase 3: Analysis (Week 3)
- [ ] Implement anomaly detection patterns
- [ ] Implement change magnitude scoring
- [ ] Implement temporal correlation analysis
- [ ] Investigation UI preparation

### Phase 4: Visualization (Week 4)
- [ ] Implement replay frame generation
- [ ] Implement animation API
- [ ] WebSocket streaming for live analysis
- [ ] Frontend integration guidance

---

## Conclusion

Layer 4 establishes the semantic graph foundation for all future temporal analysis. The stable hashing, replay sequences, and snapshot lineage are intentionally designed to support:

1. **Deterministic Diffing** (Layer 5)
2. **Anomaly Detection** (Layer 5+)
3. **Topology Evolution** (Layer 5+)
4. **Replay Animation** (Frontend)
5. **Temporal Correlation** (Investigation tools)

Layer 5 will transform these building blocks into the temporal diff engine, enabling analysts to see exactly how the behavioral network evolved during an investigation window.
