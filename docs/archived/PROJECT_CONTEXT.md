# Project Context: Behavioral Network Telemetry Platform

## Executive Summary

**PCAPModels** is a sophisticated behavioral network telemetry platform that analyzes packet capture (PCAP) files to generate behavioral insights about network hosts and their relationships.

The platform transforms raw network traffic into:
- **Canonical Events** - Normalized packet representations
- **Directional Flows** - Source-to-destination communication patterns
- **Behavioral Profiles** - Host-level risk and activity analysis
- **Semantic Graphs** - Network topology with temporal snapshots
- **NDJSON/CSV Exports** - Analyst-ready artifacts for investigation

**Current Status:** Layer 4 (Graph State) fully implemented and verified. Ready for Layer 5 (Temporal Diff Engine).

---

## Project Goals

### Primary Goals
1. **Real-time Behavioral Triage** - Identify suspicious hosts and relationships from network traffic
2. **Temporal Network Analysis** - Track topology evolution and relationship emergence
3. **Analyst-First Design** - Output designed for investigation, not false certainty
4. **Deterministic Replay** - Enable frame-by-frame reconstruction of network behavior
5. **Backend-Only Foundation** - Prepare for visualization without building frontend

### Success Criteria
- ✅ Parse 15,000+ packets in <10 seconds
- ✅ Generate behavioral indicators for 100+ hosts
- ✅ Produce reproducible, deterministic outputs
- ✅ Support temporal analysis across multiple snapshots
- ✅ Maintain <20% false positive rate for suspicious detection

---

## Technology Stack

### Core Languages & Frameworks
- **Python 3.10+** - Primary implementation language
- **Pydantic 2.x** - Data validation and serialization
- **PyShark 0.6** - Packet analysis (Wireshark Python binding)
- **Scapy 2.7** - Protocol dissection and packet construction
- **Pandas 2.3** - Data aggregation and analysis

### Data Formats
- **PCAP** - Input format (packet capture files)
- **NDJSON** - Output format (JSON newline-delimited, streaming-safe)
- **CSV** - Alternative output format for spreadsheet compatibility

### Architecture Principles
- **No ML** - Real-time performance over machine learning precision
- **No Databases** - In-memory processing with file exports
- **No Frontend** - Backend-only; frontend is responsibility of consumer
- **Deterministic** - Stable hashing and replay-safe ordering enable reproducibility

---

## Folder Structure

```
PCAPModels/
├── docs/                          ← Documentation (this folder)
│   ├── PROJECT_CONTEXT.md         ← You are here
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md
│   ├── AI_LOG.md
│   ├── MODULES.md
│   ├── RESEARCH.md
│   └── archived/
│       └── LAYER4_SURGICAL_INTEGRATION.md
│
├── ingestion/                     ← Layer 1: Packet parsing
│   ├── parse.py                   ← PCAP → canonical events
│   └── protocol_enrichment.py     ← Protocol classification
│
├── aggregation/                   ← Layer 2-3: Flow & profile aggregation
│   ├── flow_builder.py
│   ├── flow_metrics.py
│   ├── suppression.py
│   └── host_profiles.py
│
├── behavior/                      ← Layer 3-4: Behavioral analysis & graph
│   ├── schemas.py                 ← Pydantic models
│   ├── host_aggregator.py
│   ├── host_metrics.py
│   ├── host_risk.py
│   ├── host_profiles.py
│   ├── relationships.py
│   ├── baselines.py
│   ├── roles.py
│   ├── graph_builder.py           ← Layer 4: Graph entity generation
│   ├── graph_metrics.py           ← Layer 4: Graph metrics computation
│   ├── graph_state.py             ← Layer 4: Graph state & snapshots
│   └── graph_intelligence.py      ← Future: Intelligence analysis
│
├── main.py                        ← Primary execution script
├── main_new.py                    ← Development variant (keep for reference)
│
├── sample.pcap                    ← Test capture file (4.3 hours, 15K packets)
├── pyvenv.cfg                     ← Virtual environment config
│
└── data_artifacts/                ← Output directory (auto-created)
    ├── normalized_packets.ndjson
    ├── flows.ndjson
    ├── enriched_flows.ndjson
    ├── host_profiles.ndjson
    ├── relationships.ndjson
    ├── graph_nodes.ndjson        ← Layer 4
    ├── graph_edges.ndjson        ← Layer 4
    ├── graph_snapshots.ndjson    ← Layer 4
    └── graph_state.ndjson        ← Layer 4
```

---

## Current Status

### Completed Layers

#### Layer 1: Packet Ingestion
- ✅ PCAP file parsing via PyShark
- ✅ Canonical event normalization
- ✅ Timestamp preservation for replay
- ✅ Support for TCP, UDP, ICMP, DNS, TLS, HTTP

#### Layer 2: Flow Aggregation
- ✅ Directional flow construction
- ✅ Flow deduplication and merging
- ✅ TCP state tracking (SYN, ACK, RST, FIN, etc.)
- ✅ Packet and byte counting

#### Layer 3: Behavioral Scoring
- ✅ Host profile generation (104 hosts for sample capture)
- ✅ Risk scoring with multiple contributing factors
- ✅ Behavioral indicator detection
- ✅ Relationship/edge construction (201 edges for sample capture)
- ✅ Host role inference
- ✅ Suppression policy enforcement

#### Layer 4: Graph State (NEW)
- ✅ Graph node generation from host profiles
- ✅ Graph edge generation from relationships
- ✅ Lightweight graph metrics (degree, centrality, density)
- ✅ Temporal snapshot slicing (262 snapshots for 4.3-hour capture)
- ✅ Stable hashing for deterministic diffing
- ✅ Replay-safe ordering preservation
- ✅ Community detection (BFS-based connectivity clustering)
- ✅ NDJSON export of all graph artifacts

### In Progress
- 🔄 Documentation consolidation and reorganization

### Planned (Layer 5+)

#### Layer 5: Temporal Diff Engine (Q1)
- ⏳ Snapshot diffing algorithm
- ⏳ Node emergence detection
- ⏳ Relationship emergence tracking
- ⏳ Risk escalation analysis
- ⏳ Topology anomaly detection

#### Layer 5+: Future Extensions (Q2+)
- ⏳ Graph query API
- ⏳ Temporal correlation analysis
- ⏳ WebSocket streaming for live analysis
- ⏳ Visualization integration guidance

---

## Quick Start

### Prerequisites
```powershell
# Ensure Python 3.10+ and pip available
python --version

# Create and activate virtual environment
python -m venv venv
.\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt  # (or install from pyvenv.cfg)
```

### Run the Platform
```powershell
# Full pipeline with all layers
python main.py sample.pcap

# Expected output:
# - 15,512 packets parsed
# - 1,140 directional flows
# - 104 host profiles
# - 201 relationships
# - 104 graph nodes
# - 201 graph edges
# - 262 temporal snapshots
# - NDJSON + CSV exports
```

### Verify Output
```powershell
# Check graph artifacts created
Get-ChildItem graph_*.ndjson

# View first graph node
$node = Get-Content graph_nodes.ndjson -Head 1 | ConvertFrom-Json
$node | Format-List
```

### Next Steps
1. Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
2. Read [QUICKSTART_LAYER4.md](archived/QUICKSTART_LAYER4.md) for Layer 4 specifics
3. Review [ROADMAP.md](ROADMAP.md) for current and upcoming work
4. Check [DECISIONS.md](DECISIONS.md) for design rationale

---

## Known Constraints

### Performance Constraints
- **Sample Size:** Tested with 15,512 packets (4.3 hours)
- **Execution Time:** ~9 seconds end-to-end
- **Memory Usage:** ~100-200 MB peak
- **Scalability:** Linear with packet count, no exponential operations

### Design Constraints
- **No ML:** Behavioral indicators use heuristics, not machine learning
- **No Databases:** All in-memory; persistence via NDJSON/CSV exports
- **No Frontend:** Backend-only; visualization is consumer responsibility
- **No Real-Time:** Batch processing of captured traffic, not live streams

### Analytical Constraints
- **Confidence Caps:** Beacon confidence capped at 0.92, host confidence at 0.85
- **Risk Bounds:** Risk scores bounded to 0-100 with diminishing returns
- **Indicator Precision:** Analyst-first design prioritizes recall over precision
- **Incomplete Visibility:** Encrypted traffic limits protocol confidence

### Data Constraints
- **PCAP Limitations:** Cannot decrypt TLS/SSL traffic (packets only)
- **Timestamp Precision:** Depends on PCAP packet timestamp accuracy
- **Protocol Coverage:** Best with HTTP, DNS, SMB, DHCP; limited with exotic protocols
- **Replay Limitation:** Deterministic replay requires stable hashing; order matters

---

## Key Metrics (sample.pcap)

| Metric | Value | Notes |
|--------|-------|-------|
| Packet Count | 15,512 | 4.3-hour capture window |
| Flow Count | 1,140 | Directional source→target pairs |
| Host Count | 104 | Unique IP addresses |
| Relationship Count | 201 | Host-to-host connections |
| Graph Density | 0.0188 | Sparse network topology |
| High-Risk Hosts | 12 | Risk score >= 50 |
| Suspicious Edges | 6 | Relationship risk >= 35 |
| Temporal Snapshots | 262 | 1-minute windows over 4.3 hours |
| Execution Time | ~9 seconds | Full pipeline |
| Memory Peak | ~150 MB | Graph + snapshots in memory |

---

## Typical Investigation Workflow

### Step 1: Ingest Capture
```bash
python main.py suspicious_capture.pcap
```

### Step 2: Review High-Risk Hosts
```bash
# Load host_profiles.ndjson, filter risk_score >= 50
```

### Step 3: Inspect Behavioral Indicators
```bash
# Check suspicious_flows, behavioral_indicators, risk_score per host
```

### Step 4: Analyze Relationships
```bash
# Load relationships.ndjson, inspect target hosts and protocols
```

### Step 5: Examine Topology Evolution
```bash
# Load graph_snapshots.ndjson, track node/edge emergence over time
# Layer 5 will automate this (diff engine)
```

### Step 6: Correlate Findings
```bash
# Map high-risk nodes → destinations → protocols → temporal windows
# Decide if behavior warrants blocking or alerting
```

---

## Important Files & References

| File | Purpose |
|------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Complete system design and data flow |
| [ROADMAP.md](ROADMAP.md) | Project timeline and deliverables |
| [DECISIONS.md](DECISIONS.md) | Design decisions with rationale |
| [MODULES.md](MODULES.md) | Module inventory and responsibilities |
| [RESEARCH.md](RESEARCH.md) | Future enhancements and ideas |
| [AI_LOG.md](AI_LOG.md) | Development history and milestones |
| [archived/QUICKSTART_LAYER4.md](archived/QUICKSTART_LAYER4.md) | Layer 4 quick reference |
| [archived/LAYER4_GRAPH_STATE.md](archived/LAYER4_GRAPH_STATE.md) | Layer 4 technical deep-dive |
| [archived/LAYER5_PREPARATION.md](archived/LAYER5_PREPARATION.md) | Layer 5 planning and design |
| [archived/LAYER4_SURGICAL_INTEGRATION.md](archived/LAYER4_SURGICAL_INTEGRATION.md) | Layer 4 completion report |

---

## Support & Contact

### For Questions About:
- **System Architecture** → See ARCHITECTURE.md
- **Project Status** → See ROADMAP.md + AI_LOG.md
- **Design Decisions** → See DECISIONS.md
- **Implementation Details** → See module source files in behavior/, ingestion/, aggregation/
- **Future Work** → See RESEARCH.md + archived/LAYER5_PREPARATION.md

### Development Setup
- Clone repository from GitHub
- Create virtual environment: `python -m venv venv`
- Activate: `.\Scripts\Activate.ps1`
- Run: `python main.py <pcap_file>`

### Expected Outputs
- `normalized_packets.{csv,ndjson}` - Layer 1 events
- `flows.{csv,ndjson}` - Layer 2 flows
- `enriched_flows.{csv,ndjson}` - Layer 2 with scores
- `host_profiles.{csv,ndjson}` - Layer 3 profiles
- `relationships.{csv,ndjson}` - Layer 3 edges
- `graph_nodes.ndjson` - Layer 4 nodes
- `graph_edges.ndjson` - Layer 4 edges
- `graph_snapshots.ndjson` - Layer 4 temporal windows
- `graph_state.ndjson` - Layer 4 complete state

---

## Document History

| Date | Event |
|------|-------|
| Current | Project context created and consolidated |
| Previous | Layer 4 (Graph State) implementation completed |
| Earlier | Layer 3 (Host Profiles) implementation completed |
| Origin | Layer 1-2 (Packet parsing + flow aggregation) |

---

**Last Updated:** Current session  
**Status:** Active Development  
**Next Milestone:** Layer 5 (Temporal Diff Engine) Planning  
**Maintainer:** Development Team
