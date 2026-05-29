# Module Inventory & Responsibilities

Comprehensive catalog of all modules, their responsibilities, dependencies, and interfaces.

---

## Module Organization

The platform is organized into three processing layers plus schema definitions:

```
ingestion/          ← Layer 1: PCAP → Canonical Events
aggregation/        ← Layer 2: Events → Flows (+ flow metrics)
behavior/           ← Layer 3-4: Profiles → Relationships → Graph
```

---

## Layer 1: Packet Ingestion

### ingestion/parse.py

**Responsibility:** Parse PCAP files and normalize packets into canonical events.

**Key Classes:**
- `CanonicalEvent` - Normalized packet representation
- `PCAPParser` - PyShark-based PCAP reader

**Key Functions:**
- `parse_pcap_file(pcap_path)` → List[CanonicalEvent]
- `normalize_packet(pkt)` → CanonicalEvent

**Inputs:**
- PCAP files (Wireshark format)

**Outputs:**
- List[CanonicalEvent] (15,512 for sample.pcap)

**Dependencies:**
- PyShark (Wireshark Python binding)
- behavior.schemas.CanonicalEvent

**Interface (to Layer 2):**
```python
events: List[CanonicalEvent] = parse_pcap_file("sample.pcap")
```

**Key Data:**
- `packet_index` - Sequence ID (for replay)
- `timestamp` - Normalized UTC
- `src_ip`, `dst_ip`, `sport`, `dport`
- `protocol` - Application layer (HTTP, DNS, TLS, etc.)
- `flags` - TCP flags (SYN, ACK, RST, FIN, etc.)

---

### ingestion/protocol_enrichment.py

**Responsibility:** Enrich protocol classification with application-layer context.

**Key Functions:**
- `enrich_protocol(event, layers)` → ProtocolEnrichment
- `extract_tls_sni(packet)` → Optional[str]
- `extract_http_host(packet)` → Optional[str]
- `extract_dns_query(packet)` → Optional[str]

**Inputs:**
- CanonicalEvent
- PyShark packet with all layers

**Outputs:**
- ProtocolEnrichment (app_confidence, protocol_evidence)

**Dependencies:**
- PyShark (for layer access)
- behavior.schemas.ProtocolEnrichment

**Key Extractions:**
- TLS SNI (Server Name Indication)
- HTTP Host header
- DNS query names
- Well-known port mapping
- ALPN protocol

**Usage:** Called during canonical event creation in parse.py

---

## Layer 2: Flow Aggregation

### aggregation/flow_builder.py

**Responsibility:** Aggregate canonical events into directional flows.

**Key Classes:**
- `DirectionalFlow` - Source→target communication pattern
- `FlowBuilder` - Flow construction and aggregation

**Key Functions:**
- `build_flows(events)` → List[DirectionalFlow]
- `aggregate_flows(flows)` → List[DirectionalFlow]

**Inputs:**
- List[CanonicalEvent] (15,512 for sample)

**Outputs:**
- List[DirectionalFlow] (1,140 for sample)

**Dependencies:**
- behavior.schemas.DirectionalFlow, TCPStateSummary
- ingestion.parse (CanonicalEvent)

**Key Algorithms:**
- Tuple-based flow identification: (src_ip, dst_ip, sport, dport, protocol)
- TCP state aggregation (SYN, ACK, RST, FIN tracking)
- Flow deduplication

**Interface (from Layer 1, to Layer 2 metrics):**
```python
events = parse_pcap_file("sample.pcap")
flows = build_flows(events)
flows = aggregate_flows(flows)
```

**Key Data:**
- `flow_id` - Unique identifier
- `src_ip`, `dst_ip`, `sport`, `dport`
- `protocol` - Layer 4 (TCP, UDP, ICMP)
- `packet_count`, `byte_count`
- `tcp_state_summary` - Aggregated TCP flags
- `first_seen_sequence`, `last_seen_sequence` - Replay markers

---

### aggregation/flow_metrics.py

**Responsibility:** Compute metrics on flows and identify suspicious patterns.

**Key Functions:**
- `compute_flow_metrics(flows)` → List[FlowMetrics]
- `detect_beaconing(flows)` → List[BeaconCandidate]
- `compute_interval_variance(intervals)` → float
- `score_flow_suspicion(flow, metrics)` → float

**Inputs:**
- List[DirectionalFlow]

**Outputs:**
- List[FlowMetrics] (with suspicion scores, confidence)

**Dependencies:**
- aggregation.flow_builder.DirectionalFlow
- behavior.schemas.FlowMetrics

**Key Metrics:**
- Interval regularity (for beaconing detection)
- Timing variance (low = suspicious)
- Packet count sufficiency
- Application protocol confidence

**Suspicious Patterns:**
- Periodic communication (beaconing)
- Rare destination observation
- Unusual protocol context
- Asymmetric upload/download
- TCP state anomalies

**Interface:**
```python
metrics = compute_flow_metrics(flows)
suspicion_scores = [m.suspicion_score for m in metrics]
```

---

### aggregation/suppression.py

**Responsibility:** Define and enforce suppression policy for expected infrastructure.

**Key Classes:**
- `SuppressionPolicy` - Configurable suppression rules
- `DefaultSuppressionPolicy` - Built-in defaults

**Key Functions:**
- `should_suppress_flow(flow, policy)` → bool
- `create_default_policy()` → SuppressionPolicy
- `create_custom_policy(**overrides)` → SuppressionPolicy

**Inputs:**
- DirectionalFlow
- SuppressionPolicy configuration

**Outputs:**
- Boolean (True = flow should be suppressed)

**Dependencies:**
- aggregation.flow_builder.DirectionalFlow

**Default Suppressions:**
- ARP, DHCP, LLMNR, mDNS, NBNS, SSDP
- Broadcast, multicast, loopback
- Common UDP ports: 67, 68, 137, 1900, 5353, 5355

**Configuration:**
```python
policy = create_default_policy()
policy = policy.with_overrides(
    extra_ports=[8080, 3306],
    remove_protocols=["DHCP"]
)
```

**Impact:**
- Suppressed flows exported but not scored
- Dramatic false positive reduction
- Environment-specific customization

---

### aggregation/host_profiles.py

**Responsibility:** Legacy compatibility import shim.

**Current Status:** Deprecated

**Note:** Real implementation moved to behavior/host_profiles.py

**Usage:** Import redirect only
```python
from aggregation.host_profiles import build_host_profiles  # Redirects to behavior/
```

---

## Layer 3: Behavioral Analysis & Layer 4: Graph

### behavior/schemas.py

**Responsibility:** Define all Pydantic data models for the platform.

**Model Organization:**

#### Layer 1-2 Models
- `CanonicalEvent` - Normalized packet
- `DirectionalFlow` - Source→target flow
- `ProtocolEnrichment` - Protocol classification
- `TCPStateSummary` - Aggregated TCP flags

#### Layer 3 Models
- `HostProfile` - Host-level behavioral summary
- `HostRelationship` - Host-to-host connection
- `HostBaseline` - Baseline snapshot for comparison

#### Layer 4 Models
- `GraphNode` - Host in semantic graph
- `GraphEdge` - Relationship in semantic graph
- `GraphState` - Complete topology snapshot
- `TemporalSnapshot` - Time-windowed state

**Key Features:**
- All Pydantic 2.x with type hints
- JSON serialization support
- Validation on construction
- Field documentation strings

**Dependencies:**
- Pydantic >= 2.0
- Python dataclasses (for some models)

**Interface:** All downstream modules import from here
```python
from behavior.schemas import HostProfile, GraphNode, TemporalSnapshot
```

---

### behavior/host_aggregator.py

**Responsibility:** Aggregate flows into host-level profiles.

**Key Functions:**
- `aggregate_hosts(flows)` → List[HostProfile]
- `compute_host_metrics(flows_for_host)` → HostMetrics

**Inputs:**
- List[DirectionalFlow] (from Layer 2)

**Outputs:**
- List[HostProfile] (104 for sample)

**Dependencies:**
- behavior.schemas.HostProfile, HostMetrics
- aggregation.flow_builder.DirectionalFlow
- behavior.host_metrics (for metric computation)

**Aggregation Logic:**
- Group flows by initiator IP
- Aggregate responder count
- Count unique destinations
- Aggregate packet/byte totals
- Track temporal activity

**Interface:**
```python
profiles = aggregate_hosts(enriched_flows)
```

**Key Data per Profile:**
- IP address
- Initiator/responder participation counts
- External connection count
- Unique destination count
- Protocol diversity
- Flow count

---

### behavior/host_metrics.py

**Responsibility:** Compute host-level metrics.

**Key Functions:**
- `compute_host_metrics(flows_for_host)` → HostMetrics
- `compute_protocol_diversity(flows)` → int
- `compute_communication_density(flows)` → float
- `compute_temporal_activity(flows)` → Dict[str, int]

**Inputs:**
- List[DirectionalFlow] for a single host

**Outputs:**
- HostMetrics (diversity, density, activity buckets)

**Dependencies:**
- behavior.schemas.HostMetrics
- aggregation.flow_builder.DirectionalFlow

**Key Metrics:**
- Protocol diversity (count of unique protocols)
- Communication density (normalized flow intensity)
- Temporal activity buckets (hourly, daily patterns)
- Connection persistence (continuous vs episodic)

**Interface:**
```python
metrics = compute_host_metrics(flows_for_host)
print(f"Protocols: {metrics.protocol_diversity}")
```

---

### behavior/host_risk.py

**Responsibility:** Score host-level risk based on behavioral indicators.

**Key Functions:**
- `score_host_risk(profile, metrics)` → HostRisk
- `identify_host_indicators(profile)` → List[str]
- `compute_confidence(profile, metrics)` → float

**Inputs:**
- HostProfile
- HostMetrics

**Outputs:**
- HostRisk (score, confidence, indicators)

**Dependencies:**
- behavior.schemas.HostRisk, HostProfile, HostMetrics
- behavior.baselines (for baseline comparisons)
- behavior.roles (for role-based scoring)

**Risk Factors:**
- Behavioral indicators (12+ types)
- Protocol anomalies
- Communication patterns
- Destination diversity
- Upload/download asymmetry

**Confidence Decay:**
- Unknown protocol ratio
- Encrypted traffic visibility
- Low packet sample size
- Short observation window

**Bounded Confidence:**
- Maximum 0.85 (never 100%)
- Reflects analytical uncertainty

**Interface:**
```python
risk = score_host_risk(profile, metrics)
print(f"Risk: {risk.score}/100, Confidence: {risk.confidence}")
```

---

### behavior/host_profiles.py

**Responsibility:** Build complete host profiles from flows.

**Key Functions:**
- `build_host_profiles(enriched_flows)` → List[HostProfile]

**Orchestration:** Coordinates all host-level analysis:
1. Aggregation (host_aggregator)
2. Metrics computation (host_metrics)
3. Risk scoring (host_risk)
4. Role inference (roles)
5. Baseline generation (baselines)

**Inputs:**
- List[EnrichedFlow] (flows with metrics & suppression info)

**Outputs:**
- List[HostProfile] (104 for sample, fully populated)

**Dependencies:**
- behavior.host_aggregator
- behavior.host_metrics
- behavior.host_risk
- behavior.roles
- behavior.baselines

**Interface:**
```python
profiles = build_host_profiles(enriched_flows)
print(f"Built {len(profiles)} host profiles")
```

**Key Output Fields:**
- IP, hostname, inferred role
- Risk score, confidence, indicators
- Connection counts, diversity
- Temporal activity
- Baseline snapshot

---

### behavior/relationships.py

**Responsibility:** Build host-to-host relationship edges.

**Key Functions:**
- `build_relationships(profiles, flows)` → List[HostRelationship]
- `infer_relationship_type(flows_between_hosts)` → str
- `compute_relationship_risk(flows, profiles)` → float

**Inputs:**
- List[HostProfile]
- List[EnrichedFlow]

**Outputs:**
- List[HostRelationship] (201 for sample)

**Dependencies:**
- behavior.schemas.HostRelationship
- behavior.host_profiles.HostProfile
- aggregation.flow_builder.DirectionalFlow

**Relationship Types:**
- `persistent_tls` - Long-lived encrypted connection
- `periodic_dns` - Regular DNS queries
- `dhcp_assignment` - DHCP client/server
- `suspicious_communication` - Flagged interaction
- `interaction` - Normal communication

**Key Data per Relationship:**
- Source, target IPs
- Flow count, protocol set
- Persistence score
- Risk score, confidence
- Communication pattern (periodic, sporadic, etc.)

**Interface:**
```python
relationships = build_relationships(profiles, enriched_flows)
```

---

### behavior/roles.py

**Responsibility:** Infer host role from behavior and profiles.

**Key Functions:**
- `infer_host_role(profile, flows_for_host)` → str
- `identify_local_services(flows_for_host)` → List[int]
- `is_responder_dominant(flows_for_host)` → bool

**Inputs:**
- HostProfile
- List[DirectionalFlow]

**Outputs:**
- Role string: "infrastructure", "workstation", "server", "unknown"

**Dependencies:**
- behavior.schemas.HostProfile
- aggregation.flow_builder.DirectionalFlow

**Role Inference Logic:**
- `infrastructure`: Broadcast/multicast dominant, well-known services
- `workstation`: Initiator-dominant, diverse destinations
- `server`: High responder count, common ports
- `unknown`: Insufficient data

**Interface:**
```python
role = infer_host_role(profile, flows)
```

---

### behavior/baselines.py

**Responsibility:** Generate and manage baseline snapshots for comparison.

**Key Functions:**
- `create_baseline_snapshot(profile)` → HostBaseline
- `compute_baseline_hash(profile)` → str

**Inputs:**
- HostProfile

**Outputs:**
- HostBaseline (snapshot-ready dictionary)

**Dependencies:**
- behavior.schemas.HostProfile, HostBaseline

**Purpose:**
- Enable future baseline diffing
- Support behavioral drift comparison
- Prepare for Layer 5 (temporal diffs)

**Interface:**
```python
baseline = create_baseline_snapshot(profile)
```

---

### behavior/graph_builder.py

**Responsibility:** Convert host profiles and relationships into graph entities.

**Key Functions:**
- `build_graph_nodes(profiles)` → List[GraphNode]
- `build_graph_edges(relationships)` → List[GraphEdge]
- `compute_graph_hashes(nodes, edges)` → Dict

**Inputs:**
- List[HostProfile]
- List[HostRelationship]

**Outputs:**
- List[GraphNode] (104 for sample)
- List[GraphEdge] (201 for sample)
- Dict with stable hashes

**Dependencies:**
- behavior.schemas.GraphNode, GraphEdge
- behavior.host_profiles.HostProfile
- behavior.relationships.HostRelationship

**Key Algorithms:**
- Identity mapping (IP → node_id hash)
- Relationship type inference
- Communication pattern inference
- Stable hash computation

**Interface:**
```python
nodes = build_graph_nodes(profiles)
edges = build_graph_edges(relationships)
hashes = compute_graph_hashes(nodes, edges)
```

---

### behavior/graph_metrics.py

**Responsibility:** Compute lightweight graph-level metrics.

**Key Functions:**
- `compute_graph_metrics(nodes, edges)` → GraphMetrics
- `compute_community_detection(nodes, edges)` → Dict[str, List[str]]

**Inputs:**
- List[GraphNode]
- List[GraphEdge]

**Outputs:**
- GraphMetrics (degree, centrality, density)
- Communities (connectivity clustering)

**Dependencies:**
- behavior.schemas.GraphNode, GraphEdge, GraphMetrics
- (no external ML libraries)

**Metrics Computed:**
- Node degree, weighted degree
- Centrality hint (simplified)
- Node priority (risk × centrality)
- Communication density
- Graph density, avg degree
- Graph risk score
- Isolated node count

**Algorithms:**
- No PageRank (too expensive)
- No eigenvector centrality
- Simple BFS for community detection

**Interface:**
```python
metrics = compute_graph_metrics(nodes, edges)
communities = compute_community_detection(nodes, edges)
```

---

### behavior/graph_state.py

**Responsibility:** Build complete graph states and temporal snapshots.

**Key Functions:**
- `build_graph_state(profiles, relationships)` → GraphState
- `build_temporal_snapshots(profiles, relationships, interval=60)` → List[TemporalSnapshot]

**Inputs:**
- List[HostProfile]
- List[HostRelationship]
- Optional: snapshot_interval_seconds (default 60)

**Outputs:**
- GraphState (single complete snapshot)
- List[TemporalSnapshot] (262 for 4.3-hour capture)

**Dependencies:**
- behavior.graph_builder
- behavior.graph_metrics
- behavior.schemas.GraphState, TemporalSnapshot

**Orchestration:**
1. Build nodes and edges
2. Compute graph metrics
3. Compute stable hashes
4. Determine temporal boundaries
5. Slice into windows
6. Build per-window graph states

**Interface:**
```python
graph_state = build_graph_state(profiles, relationships)
snapshots = build_temporal_snapshots(profiles, relationships, interval_seconds=60)
```

**Output Data:**
- GraphState: node_count, edge_count, density, risk_score, high_centrality_nodes
- TemporalSnapshot: window_start, window_end, active_nodes, active_edges, graph_state

---

### behavior/graph_intelligence.py

**Responsibility:** Future intelligence analysis module (placeholder).

**Current Status:** Stub for future expansion

**Planned Functions:**
- Correlation analysis across snapshots
- Temporal pattern detection
- Investigation context preparation

**Note:** Will be heavily used in Layer 5 (Temporal Diff Engine)

---

## Main Entry Point

### main.py

**Responsibility:** Orchestrate entire pipeline from PCAP input to artifact export.

**Pipeline Steps:**
```
STEP 1-2: Packet ingestion → canonical events
STEP 3: Flow aggregation
STEP 4: Flow metrics → enriched flows
STEP 5: Host profiles + relationships (Layer 3)
STEP 6: Graph state + metrics (Layer 4)
STEP 7: Temporal snapshots (Layer 4)
STEP 8: Analysis summary + graph summary
STEP 9: Export artifacts (CSV + NDJSON)
```

**Key Functions:**
- `main(pcap_path, no_csv, no_ndjson)` - Primary entry point
- `_print_analysis_summary()` - Output formatting
- `_print_graph_summary()` - Layer 4 output
- `events_to_ndjson()` - NDJSON export
- `events_to_csv()` - CSV export

**Command Line:**
```bash
python main.py sample.pcap [--no-csv] [--no-ndjson]
```

**Expected Execution Time:** ~9 seconds for sample.pcap

**Output Files:**
- normalized_packets.{csv,ndjson}
- flows.{csv,ndjson}
- enriched_flows.{csv,ndjson}
- host_profiles.{csv,ndjson}
- relationships.{csv,ndjson}
- graph_nodes.ndjson
- graph_edges.ndjson
- graph_snapshots.ndjson
- graph_state.ndjson

---

## Dependency Graph

```
Layer 1 (Ingestion)
├── ingestion/parse.py
└── ingestion/protocol_enrichment.py

Layer 2 (Flow Aggregation)
├── aggregation/flow_builder.py
├── aggregation/flow_metrics.py
└── aggregation/suppression.py

Layer 3 (Behavioral Scoring)
├── behavior/host_aggregator.py
├── behavior/host_metrics.py
├── behavior/host_risk.py
├── behavior/roles.py
├── behavior/baselines.py
├── behavior/host_profiles.py (orchestrator)
└── behavior/relationships.py

Layer 4 (Graph State)
├── behavior/graph_builder.py
├── behavior/graph_metrics.py
├── behavior/graph_state.py (orchestrator)
└── behavior/graph_intelligence.py (stub)

Shared
├── behavior/schemas.py (all models)
├── main.py (orchestrator)
└── [test data] sample.pcap
```

---

## Module Metrics

### Code Organization

| Module | Lines | Purpose | Complexity |
|--------|-------|---------|------------|
| schemas.py | 800+ | Data models | Medium |
| parse.py | 250+ | PCAP parsing | Medium |
| protocol_enrichment.py | 200+ | Protocol classification | Low |
| flow_builder.py | 300+ | Flow aggregation | Medium |
| flow_metrics.py | 350+ | Flow analysis | High |
| suppression.py | 150+ | Suppression policy | Low |
| host_aggregator.py | 200+ | Host aggregation | Medium |
| host_metrics.py | 200+ | Host metrics | Medium |
| host_risk.py | 300+ | Risk scoring | High |
| host_profiles.py | 150+ | Profile orchestration | Medium |
| relationships.py | 250+ | Relationship building | Medium |
| roles.py | 150+ | Role inference | Low |
| baselines.py | 100+ | Baseline snapshots | Low |
| graph_builder.py | 220+ | Graph entity generation | Medium |
| graph_metrics.py | 180+ | Graph metrics | Medium |
| graph_state.py | 280+ | State building | Medium |
| main.py | 400+ | Pipeline orchestration | High |

---

## Performance Characteristics

### Execution Time (sample.pcap)

| Module | Time | Packets |
|--------|------|---------|
| parse.py | 0.5s | 15,512 → 15,512 events |
| flow_builder.py | 0.3s | 15,512 → 1,140 flows |
| flow_metrics.py | 0.4s | 1,140 flows scored |
| host_aggregator.py | 0.2s | 1,140 → 104 profiles |
| host_risk.py | 0.2s | Risk scoring |
| relationships.py | 0.2s | 201 relationships |
| graph_builder.py | 0.8s | Graph generation |
| graph_metrics.py | 0.0s | Metrics computation |
| graph_state.py | 4.2s | 262 snapshots |
| **Total** | **~9s** | Full pipeline |

---

## Integration Interfaces

### Layer 1 → Layer 2
```python
events = parse_pcap_file(pcap_path)  # List[CanonicalEvent]
flows = build_flows(events)          # List[DirectionalFlow]
```

### Layer 2 → Layer 3
```python
enriched_flows = compute_flow_metrics(flows)  # With suspicion scores
profiles = build_host_profiles(enriched_flows)
relationships = build_relationships(profiles, enriched_flows)
```

### Layer 3 → Layer 4
```python
graph_state = build_graph_state(profiles, relationships)
snapshots = build_temporal_snapshots(profiles, relationships)
```

### Layer 4 → Export
```python
events_to_ndjson(graph_state.nodes, "graph_nodes.ndjson")
events_to_ndjson(graph_state.edges, "graph_edges.ndjson")
events_to_ndjson(snapshots, "graph_snapshots.ndjson")
```

---

## Testing Strategy

### Unit Tests (Per Module)
- [ ] parse.py: PCAP parsing, normalization
- [ ] flow_builder.py: Flow deduplication, TCP state
- [ ] host_aggregator.py: Aggregation logic
- [ ] host_risk.py: Risk scoring, confidence
- [ ] graph_builder.py: Node/edge generation
- [ ] graph_metrics.py: Metric calculations

### Integration Tests (End-to-End)
- [ ] main.py: Full pipeline with sample.pcap
- [ ] Export: Verify NDJSON/CSV correctness
- [ ] Temporal: Verify snapshot continuity

### Performance Tests
- [ ] Time per step (< 10 seconds total)
- [ ] Memory usage (< 500 MB)
- [ ] Scalability (100K+ packets)

---

## Future Extensions (Layer 5+)

### behavior/temporal_diff.py (Planned)
- Snapshot diffing
- Change detection
- Anomaly scoring

### behavior/investigation_api.py (Planned)
- Graph queries
- Temporal correlation
- Investigation context

### behavior/visualization_prep.py (Planned)
- Frontend payload formatting
- Animation frame generation
- WebSocket streaming

---

## Maintenance & Upgrades

### Adding a New Feature
1. Propose change to DECISIONS.md
2. Add model to schemas.py if needed
3. Implement in relevant module
4. Add tests
5. Update MODULES.md
6. Document in ARCHITECTURE.md

### Updating a Module
- Maintain backward compatibility with consuming modules
- Update type hints and docstrings
- Run full pipeline verification (main.py)
- Update tests

### Performance Optimization
- Profile with sample.pcap first
- Measure before/after
- Verify no correctness regression
- Document change in git commit

---

## Summary Table

| Layer | Modules | Purpose | Output |
|-------|---------|---------|--------|
| **1** | parse, protocol_enrichment | Packet parsing | Canonical events |
| **2** | flow_builder, flow_metrics, suppression | Flow analysis | Enriched flows |
| **3** | host_aggregator, host_metrics, host_risk, relationships, roles, baselines | Behavioral scoring | Host profiles + relationships |
| **4** | graph_builder, graph_metrics, graph_state | Topology analysis | Graph nodes/edges + snapshots |

---

**Document Status:** Active  
**Last Updated:** Current session  
**Maintainer:** Development Team  
**Next Review:** Layer 5 kickoff
