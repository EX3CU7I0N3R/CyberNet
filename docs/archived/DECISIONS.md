# Design Decisions Log

Comprehensive record of architectural and technical decisions with rationale, date, and impact.

---

## Layer 1: Packet Ingestion

### Decision 1.1: PyShark for Packet Analysis

**Decision:** Use PyShark (Python Wireshark binding) instead of scapy-only or raw socket parsing.

**Rationale:**
- PyShark provides deep packet inspection with Wireshark's parsing engine
- Supports 100+ protocols with automatic dissection
- Reduces need for custom protocol parsing
- Integrates with existing Wireshark plugins and features
- PCAP file reading built-in

**Alternatives Considered:**
- Scapy alone (too verbose for all protocols)
- dpkt (older, limited protocol support)
- tshark command-line (slow, parsing overhead)
- Raw socket parsing (too low-level)

**Impact:**
- ✅ Fast protocol enrichment (TLS SNI, HTTP Host, DNS queries)
- ✅ Consistent protocol classification
- ⚠️ PyShark slower than scapy for raw access (mitigated by caching)

**Date:** Design phase (pre-Layer 4)

---

### Decision 1.2: Canonical Event Normalization

**Decision:** Create normalized "canonical events" as first processing layer before flow aggregation.

**Rationale:**
- Standardize across packet types and protocols
- Enable replay-safe timestamp ordering
- Prepare for deterministic reconstruction
- Decouple packet parsing from behavioral analysis

**Data Structure:**
```python
CanonicalEvent:
  - packet_index (sequence for replay)
  - timestamp (normalized UTC)
  - src_ip, dst_ip, sport, dport
  - protocol, flags, payload_size
```

**Impact:**
- ✅ Enables deterministic replay via packet_index
- ✅ Simplifies downstream processing
- ⚠️ Additional memory overhead (mitigated by streaming export)

**Date:** Layer 1 design

---

## Layer 2-3: Behavioral Analysis

### Decision 2.1: Directional Flows (Not Bidirectional)

**Decision:** Create and maintain separate source→target and target→source flows instead of single bidirectional flow.

**Rationale:**
- Preserves asymmetric behavior (uploader vs downloader)
- Enables persistent communication pattern detection
- Captures unidirectional scanning and beaconing
- Simpler analysis of initiator-responder roles

**Trade-off:**
- 2x more flow objects in memory
- Requires relationship aggregation for bidirectional views

**Impact:**
- ✅ Detects asymmetric attacks (upload-heavy beacons)
- ✅ Preserves initiator/responder context
- ✅ Enables role inference (server, workstation, scanner)

**Date:** Layer 2 design

---

### Decision 2.2: Multiple Contributing Factors for Risk

**Decision:** Single-factor detections removed; suspicion now requires multiple contributing indicators.

**Rationale:**
- Reduce false positives from single anomaly
- Analyst-first design: investigation not accusation
- Confidence model reflects uncertainty
- Example: Periodic behavior + external destination + unusual port = suspicious, not just one factor

**Thresholds:**
- Minimum 2 indicators for suspicion flag
- Confidence bounded 0-0.92 (never 100%)
- Risk score additive with diminishing returns

**Impact:**
- ✅ Significantly fewer false positives
- ⚠️ May miss isolated anomalies
- ✅ Analyst gets context (indicator_details) for scoring

**Date:** Layer 3 design

---

### Decision 2.3: Behavioral Indicators (Analyst-Safe Terminology)

**Decision:** Use non-assertive terms for detection outputs (avoid "malicious", "attack", "threat").

**Example Indicators:**
- `potential_beaconing_behavior` (not "beacon detected")
- `periodic_low_volume_communication` (not "C&C activity")
- `rare_destination_observed` (not "lateral movement")
- `unusual_protocol_context` (not "protocol abuse")

**Rationale:**
- Avoid influencing analyst interpretation
- Enable correlation with other data sources
- Preserve investigative neutrality
- Example: "periodic_low_volume_communication" could be monitoring, backup, or C&C

**Impact:**
- ✅ Analysts make conclusions, not AI
- ✅ Enables correlation with external context
- ✅ Reduces liability for false classifications

**Date:** Layer 3 design

---

### Decision 2.4: Suppression Policy for Infrastructure

**Decision:** Built-in suppression for expected infrastructure traffic before scoring.

**Suppressed by Default:**
- ARP, DHCP, LLMNR, mDNS, NBNS, SSDP
- Broadcast, multicast, loopback traffic
- Common UDP service ports (67, 68, 137, 1900, 5353, 5355)

**Rationale:**
- Noisy infrastructure traffic inflates false positive rate
- Environment-specific; policy can be overridden
- Suppressed flows still exported and counted
- Enables site-specific allowlisting

**Impact:**
- ✅ Dramatic false positive reduction
- ✅ Focuses on meaningful behavior
- ✅ Exportable interface for policy customization

**Date:** Layer 3 design

---

### Decision 2.5: Confidence Model (Bounded, Not Percentage)

**Decision:** Confidence scores bounded [0.0, 0.92] for beacons, [0.0, 0.85] for hosts; never reach 100%.

**Rationale:**
- Acknowledges telemetry uncertainty
- Prevents false certainty in scoring
- Analyst knows more data is needed for confirmation
- Example: 0.92 confidence beacon still needs corroboration

**Derivation:**
- **Beacon confidence:** interval_count, observed_duration, timing_variance, app_protocol_confidence, packet_count
- **Host confidence:** flow_count, packet_sample_size, active_duration, protocol_reliability, metric_stability

**Impact:**
- ✅ Honest uncertainty representation
- ✅ Prevents over-confident false positives
- ✅ Encourages multi-source correlation

**Date:** Layer 3 design

---

## Layer 4: Graph State

### Decision 4.1: Lightweight Metrics Over ML

**Decision:** Compute lightweight graph metrics (degree, centrality heuristics) instead of ML algorithms.

**Metrics Included:**
- Node degree, weighted degree
- Centrality hint (heuristic, not PageRank)
- Graph density, avg degree
- Simple BFS-based community detection

**Alternatives Rejected:**
- PageRank (too expensive, non-deterministic)
- Eigenvector centrality (expensive)
- ML anomaly detection (non-reproducible)
- Spectral analysis (expensive)

**Rationale:**
- Real-time performance required (sub-10 second execution)
- Deterministic replay essential (no randomness)
- Analyst needs to understand scoring
- No ML model to maintain/update

**Impact:**
- ✅ Fast execution (~0.8s for graph metrics)
- ✅ Deterministic reproducibility
- ✅ Transparent to analyst
- ✅ No model dependency
- ⚠️ Less sophisticated centrality measures

**Date:** Layer 4 design

---

### Decision 4.2: Time-Windowed Snapshots (60-second default)

**Decision:** Generate temporal snapshots at 60-second intervals (configurable).

**Rationale:**
- Balance between temporal granularity and data volume
- 60 seconds captures behavior changes but not micro-transactions
- 4.3-hour capture → 262 snapshots (manageable for animation)
- Customizable via parameter for other use cases

**Alternatives:**
- 1-second windows: Too granular, ~15,000 snapshots
- 5-minute windows: Too coarse, miss emergence patterns
- 1-minute windows: Sweet spot (262 snapshots for 4.3h)

**Impact:**
- ✅ 262 snapshots is replay-friendly
- ✅ Captures meaningful topology changes
- ✅ NDJSON size manageable (17.3 MB for sample)
- ⚠️ Some micro-behavior lost in 60-second window

**Date:** Layer 4 design

---

### Decision 4.3: Stable Hashing for Deterministic Diffing

**Decision:** Compute stable hashes on node/edge entities to enable future diffing without ML.

**Hashing Strategy:**
- Node hash: `sha256(node_id:risk_score:behavioral_indicators)`
- Edge hash: `sha256(source:target:risk_score)`
- Graph fingerprint: `sha256(sorted(all_hashes))`

**Rationale:**
- Enable Layer 5 diff engine without ML
- Deterministic: same inputs = same hash
- Quick comparison (hash lookup, set operations)
- Enables node emergence detection (hash appears in t1 but not t0)

**Impact:**
- ✅ Enables deterministic diffing
- ✅ Quick topology change detection
- ✅ No ML dependency for anomaly detection
- ✅ Reproducible across runs

**Date:** Layer 4 design

---

### Decision 4.4: Replay-Safe Ordering (Sequence Markers)

**Decision:** Preserve deterministic ordering via replay_sequence_start/end on all entities.

**Markers:**
- `replay_sequence_start`: Packet index at first activity
- `replay_sequence_end`: Packet index at last activity
- Deterministic ordering within snapshots by sequence

**Rationale:**
- Enable frame-by-frame reconstruction
- Bit-identical replay across runs
- Support for future animation/visualization
- Audit trail for temporal causality

**Impact:**
- ✅ Deterministic replay guaranteed
- ✅ Frame-by-frame animation possible
- ✅ Causality auditable
- ✅ Future Layer 5 foundation

**Date:** Layer 4 design

---

### Decision 4.5: NDJSON Export Format (Not JSON)

**Decision:** Export graph artifacts as NDJSON (JSON newline-delimited) not single JSON file.

**Rationale:**
- Stream-safe (one entity per line)
- Database-agnostic (can load into any system)
- Frontend-ready (incrementally load)
- Efficient for large datasets (no load entire file)
- Compatible with WebSocket streaming (future)

**File Structure:**
```
{"node_id": "...", ...}
{"node_id": "...", ...}
{"node_id": "...", ...}
```

**Impact:**
- ✅ Streaming-safe
- ✅ Database-independent
- ✅ Incremental loading
- ✅ Large file friendly
- ✅ WebSocket compatible

**Date:** Layer 4 design

---

### Decision 4.6: Backend-Only (No Frontend)

**Decision:** Layer 4 produces graph artifacts only; no frontend rendering, visualization, or UI.

**Rationale:**
- Keeps scope focused on data layer
- Visualization is consumer responsibility
- Supports multiple visualization tools (D3, Cytoscape, Sigma.js)
- Faster time to core functionality
- Data-layer reusable across multiple frontends

**Future Options:**
- Visualization library wraps NDJSON exports
- Custom D3.js frontend
- Graph database (Neo4j) import
- BI tool integration (Tableau, PowerBI)

**Impact:**
- ✅ Focused scope
- ✅ Reusable across tools
- ✅ Faster delivery
- ✅ Lower maintenance burden
- ⚠️ Consumer must build visualization

**Date:** Layer 4 design

---

## Layer 5: Future (Planned)

### Decision 5.1: Temporal Diff Engine (Not Incremental Update)

**Decision:** Layer 5 will use snapshot diffing (compare t0 vs t1) rather than incremental updates.

**Rationale:**
- Simpler algorithm (set operations: emerged, disappeared, changed)
- Deterministic comparison
- Works with existing stable hashes
- Replay-safe: can compare any two snapshots
- Enables anomaly detection patterns

**Alternative (Rejected):** Incremental updates
- Harder to reason about
- Order-dependent
- Not replay-safe

**Impact:**
- ✅ Simple, maintainable algorithm
- ✅ Deterministic results
- ✅ Replay-safe
- ✅ Foundation for anomaly detection

**Date:** Layer 5 planning

---

### Decision 5.2: Change Magnitude Scoring (Not Just Binary)

**Decision:** Layer 5 will score change magnitude (0-1) rather than just detecting changes.

**Rationale:**
- Not all changes are equal (1 new node vs 50 new nodes)
- Analysts need severity assessment
- Enables anomaly thresholding
- Example: 0.95 magnitude = major topology shift, investigate immediately

**Approach:**
- Weighted factors: node emergences, edge emergences, risk escalations
- Normalized to 0-1 scale
- Comparable across time windows

**Impact:**
- ✅ Enables severity-based alerting
- ✅ Reduces alert fatigue
- ✅ Prioritizes investigation

**Date:** Layer 5 planning

---

## Cross-Layer Decisions

### Decision C.1: CSV + NDJSON Dual Export

**Decision:** Export all artifacts in both CSV (spreadsheet) and NDJSON (streaming) formats.

**Rationale:**
- CSV for analyst spreadsheet workflows
- NDJSON for programmatic systems, databases, visualization
- No duplication (same data, different serialization)
- User choice via `--no-csv` or `--no-ndjson` flags

**Impact:**
- ✅ Supports both analyst and programmatic workflows
- ✅ No forced migration to one format
- ⚠️ 2x storage for exports (mitigated by small file sizes)

**Date:** Layer 2 design

---

### Decision C.2: Pydantic for All Models

**Decision:** Use Pydantic 2.x for all data models (events, flows, profiles, graphs).

**Rationale:**
- Type safety and validation
- Automatic JSON serialization
- IDE support and autocomplete
- No manual serialization code
- Version upgrade friendly

**Impact:**
- ✅ Type-safe throughout
- ✅ Automatic validation
- ✅ JSON export trivial
- ✅ Maintainable models

**Date:** Layer 1 design

---

### Decision C.3: In-Memory Only (No Persistence Layer)

**Decision:** All processing in-memory; results exported to NDJSON/CSV files.

**Rationale:**
- Simpler architecture (no database)
- Faster execution (no database overhead)
- Easier deployment (no DB setup)
- Data export (NDJSON) enables integration with any system
- Sample capture (15K packets) fits in memory (~100-200 MB)

**Scalability Plan:**
- For larger captures: stream processing instead of batch
- For operational deployment: integrate with database via NDJSON export
- No in-memory bottleneck for streaming architecture

**Impact:**
- ✅ Simple deployment
- ✅ Fast execution
- ✅ No DB maintenance
- ✅ Flexible integration
- ⚠️ Memory-bound for very large captures (future stream processing)

**Date:** Layer 1 design

---

## Risk and Uncertainty Log

### Risk 1: PyShark Dependency

**Risk:** PyShark is less actively maintained than Scapy.

**Mitigation:**
- Scapy fallback for protocol enrichment
- Can replace PyShark with custom parsing if needed
- Scapy already included in dependencies

**Status:** Low risk, monitored

---

### Risk 2: Hashing Collisions

**Risk:** SHA256 collisions (extremely unlikely but not impossible).

**Mitigation:**
- For practical datasets, collision risk negligible
- Can upgrade to SHA512 if required
- Multiple hash checks in validation

**Status:** Low risk, acceptable

---

### Risk 3: Large Capture Scaling

**Risk:** In-memory processing may not scale to multi-GB captures.

**Mitigation:**
- Stream processing for large files (future)
- NDJSON exports support incremental loading
- Current design tested to 15K packets (success)
- Scalability planned for Layer 5+

**Status:** Known limitation, acceptable for current scope

---

### Risk 4: Replay Sequence Collisions

**Risk:** Same packet_index assigned to multiple packets.

**Mitigation:**
- PyShark preserves packet order
- Sequence ID validated during canonical event creation
- Tests verify deterministic ordering

**Status:** Low risk, monitored

---

## Decision Review Schedule

| Decision | Last Reviewed | Next Review | Status |
|----------|---------------|-------------|--------|
| 1.1: PyShark | Design phase | Layer 5+ | ✅ Active |
| 2.1: Directional flows | Layer 3 | Layer 5 | ✅ Active |
| 2.2: Multiple factors | Layer 3 | Never | ✅ Core principle |
| 2.3: Safe terminology | Layer 3 | Never | ✅ Core principle |
| 2.4: Suppression policy | Layer 3 | Layer 5+ | ✅ Active |
| 4.1: Lightweight metrics | Layer 4 | Layer 5 | ✅ Active |
| 4.2: 60s snapshots | Layer 4 | Layer 5 | ✅ Active |
| 4.3: Stable hashing | Layer 4 | Layer 5+ | ✅ Active |
| 5.1: Diff engine | Layer 5 planning | Layer 5 impl | ⏳ Pending |

---

## Glossary of Terms

| Term | Definition |
|------|-----------|
| **Canonical Event** | Normalized packet representation (Layer 1) |
| **Directional Flow** | Source→Target communication pattern (Layer 2) |
| **Host Profile** | Aggregated behavioral summary per host (Layer 3) |
| **Graph Node** | Host representation in semantic graph (Layer 4) |
| **Graph Edge** | Relationship representation in semantic graph (Layer 4) |
| **Temporal Snapshot** | Time-windowed graph state (Layer 4) |
| **Replay Sequence** | Deterministic packet ordering for reproducibility |
| **Stable Hash** | Deterministic hash for comparison across runs |
| **Anomaly** | Statistically significant deviation from expected |
| **Confidence** | Certainty in assessment (bounded 0-0.92) |
| **Risk Score** | Behavioral risk assessment (0-100) |
| **Suppression** | Filtering expected infrastructure traffic |

---

## Acknowledgments

These decisions reflect:
- Network security domain expertise
- Practical constraints of PCAP analysis
- Analyst-first design philosophy
- Reproducibility and determinism requirements
- Layer 4 verification with sample.pcap (15.5K packets)

---

**Document Status:** Active - Layer 4 complete, Layer 5 planning  
**Last Updated:** Current session  
**Maintainer:** Development team  
**Next Review:** Layer 5 implementation begins
