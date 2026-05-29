# Layer 4 Quick Start Guide

## Running the Platform with Layer 4

### Prerequisites
```powershell
# Ensure you're in the workspace
cd c:\Users\siddh\VSCodeFiles\PCAPModels

# Activate virtual environment
& .\Scripts\Activate.ps1
```

### Run Full Pipeline (with Layer 4)
```powershell
python main.py sample.pcap
```

**Expected Output Duration:** ~10 seconds

**Expected Output Sections:**
1. STEP 1-5: Packet ingestion through host profiles (existing)
2. **STEP 6: Building graph state** (NEW)
3. **STEP 7: Generating temporal snapshots** (NEW)
4. STEP 8: Analysis summary + **GRAPH STATE SUMMARY** (NEW section)
5. STEP 9: Exporting artifacts + **graph_*.ndjson files** (NEW files)

---

## Verifying Layer 4 Output

### Check Graph Artifacts Were Created
```powershell
# List all graph files
Get-ChildItem graph_*.* | Format-Table Name, Length

# Expected files:
# - graph_nodes.ndjson      (~200-300 KB)
# - graph_edges.ndjson      (~100-200 KB)
# - graph_snapshots.ndjson  (~15-20 MB)
# - graph_state.ndjson      (~300-400 KB)
```

### View Graph State Summary in Output
```powershell
# Run and capture output
python main.py sample.pcap 2>&1 | Select-String -Pattern "GRAPH STATE SUMMARY" -A 30
```

**Should show:**
```
Graph Nodes: 104
Graph Edges: 201
Graph Density: 0.018764
Graph Risk Score: 25.6
Isolated Nodes: 0

High Centrality Nodes:
  - 10.2.28.88
  - 0.0.0.0
  - ...

Temporal Snapshots: 262 generated
```

### Inspect Graph Nodes
```powershell
# View first graph node
$node = Get-Content graph_nodes.ndjson -Head 1 | ConvertFrom-Json
$node | Select-Object node_id, ip_address, risk_score, node_degree | Format-List
```

### Inspect Graph Edges
```powershell
# View first graph edge
$edge = Get-Content graph_edges.ndjson -Head 1 | ConvertFrom-Json
$edge | Select-Object edge_id, source_node, target_node, relationship_type, relationship_risk | Format-List
```

### Inspect Temporal Snapshots
```powershell
# View first temporal snapshot
$snapshot = Get-Content graph_snapshots.ndjson -Head 1 | ConvertFrom-Json
$snapshot | Select-Object snapshot_id, window_start, window_end, node_count, edge_count, active_nodes | Format-List
```

### Inspect Graph State
```powershell
# View graph state
$state = Get-Content graph_state.ndjson | ConvertFrom-Json
$state | Select-Object snapshot_id, timestamp, node_count, edge_count, graph_density, graph_risk_score | Format-List
```

---

## Understanding the Output

### Graph State Summary Fields

| Field | Meaning | Example |
|-------|---------|---------|
| Graph Nodes | Total hosts in network | 104 |
| Graph Edges | Total relationships | 201 |
| Graph Density | Sparsity (0-1 range) | 0.0188 = sparse network |
| Graph Risk Score | Average risk of important nodes | 25.6 / 100 = moderate |
| Isolated Nodes | Hosts with no connections | 0 = all connected |
| High Centrality Nodes | Most important hosts | 10.2.28.88 is most central |
| Relationship Types | Types of connections | persistent_tls, periodic_dns, etc. |
| Temporal Snapshots | Time-windowed views | 262 = 1-minute windows |
| Average Node Degree | Avg connections per host | 1.99 connections |
| Suspicious Edges | High-risk relationships | 6 edges flagged |
| Network Communities | Disconnected clusters | 1 = all connected |

### Replay Metadata

```
Sequence start: 2       ← First packet index in capture
Sequence end: 15511     ← Last packet index in capture
```

This enables **deterministic replay** of the network evolution.

---

## Performance Baseline

For sample.pcap (15,512 packets, 1,140 flows, 104 hosts):

| Step | Time | Notes |
|------|------|-------|
| Steps 1-5 | ~2 sec | Existing layers |
| Step 6 (Graph build) | ~0.8 sec | Node/edge creation + metrics |
| Step 7 (Snapshots) | ~4.2 sec | 262 time-windowed snapshots |
| Step 8 (Summary) | <0.1 sec | Print output |
| Step 9 (Exports) | ~2.0 sec | CSV + NDJSON |
| **Total** | **~9 sec** | Full pipeline |

**Memory Usage:** ~100-200 MB peak

---

## Common Tasks

### Export Only (No CSV)
```powershell
python main.py sample.pcap --no-csv
```

### Skip NDJSON (CSV Only)
```powershell
python main.py sample.pcap --no-ndjson
```

### Analyze Different PCAP
```powershell
python main.py your_capture.pcap
```

**Output files will be created in same directory.**

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pyshark'"

**Solution:** Activate virtual environment first
```powershell
& .\Scripts\Activate.ps1
python main.py sample.pcap
```

### Issue: No graph_*.ndjson files created

**Solution:** Check if export section ran
```powershell
python main.py sample.pcap 2>&1 | Select-String "NDJSON"
# Should show "[OK] Wrote NDJSON artifacts"
```

If not shown, check for errors in STEP 6-7.

### Issue: "Graph Nodes: 0" in output

**Solution:** Verify host profiles were created
```powershell
python main.py sample.pcap 2>&1 | Select-String "Built.*profiles"
# Should show "[OK] Built 104 host profiles"
```

### Issue: Very small graph_snapshots.ndjson file

**Solution:** Check timestamp validity in profiles
```powershell
$profiles = Get-Content host_profiles.ndjson | ConvertFrom-Json
$profiles[0] | Select-Object first_seen, last_seen
# Both should be valid ISO timestamps
```

---

## Data Processing Pipeline

```
┌─ sample.pcap ─────────────────────────────────┐
│  15,512 packets (4.3 hour capture)              │
└────────────────────────────────────────────────┘
                    │
                    ▼ STEP 1-2
        ┌─ 15,512 canonical events ─┐
        │ (normalized packets)        │
        └─────────────────────────────┘
                    │
                    ▼ STEP 3
        ┌─ 1,140 directional flows ──┐
        │ (source → target pairs)      │
        └─────────────────────────────┘
                    │
                    ▼ STEP 4
        ┌─ 1,140 enriched flows ─────┐
        │ (with behavioral scores)     │
        └─────────────────────────────┘
                    │
                    ▼ STEP 5
        ┌─ 104 host profiles ────────┐
        │ 201 relationships            │
        └─────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          ▼ STEP 6            │
    ┌─ 104 graph nodes ─┐    │
    │ 201 graph edges    │    │
    │ 1 graph state      │    │
    └────────────────────┘    │
          │                   │
          └─────────┬─────────┘
                    ▼ STEP 7
        ┌─ 262 temporal snapshots ──┐
        │ (60-second windows)         │
        └─────────────────────────────┘
                    │
                    ▼ STEP 8
        ┌─ Analysis + Graph Summary ─┐
        │ (runtime output)             │
        └─────────────────────────────┘
                    │
                    ▼ STEP 9
        ┌─ Artifact Exports ─────────┐
        │ normalized_packets.{csv,ndjson}  │
        │ flows.{csv,ndjson}               │
        │ enriched_flows.{csv,ndjson}      │
        │ host_profiles.{csv,ndjson}       │
        │ relationships.{csv,ndjson}       │
        │ graph_nodes.ndjson         │
        │ graph_edges.ndjson         │
        │ graph_snapshots.ndjson     │
        │ graph_state.ndjson         │
        │ host_baseline_snapshot.ndjson │
        └─────────────────────────────┘
```

---

## Working with Graph Artifacts

### Load All Graph Nodes (Python)
```python
import json

nodes = []
with open("graph_nodes.ndjson", "r") as f:
    for line in f:
        nodes.append(json.loads(line))

print(f"Loaded {len(nodes)} nodes")

# Access first node
first_node = nodes[0]
print(f"Node: {first_node['ip_address']}")
print(f"Risk Score: {first_node['risk_score']}")
print(f"Degree: {first_node['node_degree']}")
```

### Filter High-Risk Edges (PowerShell)
```powershell
$edges = @()
Get-Content graph_edges.ndjson | ForEach-Object {
    $edges += $_ | ConvertFrom-Json
}

$highRisk = $edges | Where-Object { $_.relationship_risk -ge 35 }
$highRisk | Select-Object source_node, target_node, relationship_risk, relationship_type
```

### Analyze Temporal Snapshots (Python)
```python
import json

snapshots = []
with open("graph_snapshots.ndjson", "r") as f:
    for line in f:
        snapshots.append(json.loads(line))

# Find snapshot with most nodes
max_snapshot = max(snapshots, key=lambda s: s['node_count'])
print(f"Peak activity: {max_snapshot['node_count']} nodes at {max_snapshot['window_start']}")

# Find snapshot with most edges
max_edges = max(snapshots, key=lambda s: s['edge_count'])
print(f"Peak relationships: {max_edges['edge_count']} edges at {max_edges['window_start']}")
```

---

## Next Steps

### For Immediate Use
1. ✅ Run the pipeline: `python main.py sample.pcap`
2. ✅ Verify graph artifacts are created
3. ✅ Review LAYER4_GRAPH_STATE.md for field documentation
4. ✅ Load artifacts into your analysis tool

### For Layer 5 Development
1. 📖 Review LAYER5_PREPARATION.md
2. 📖 Understand snapshot diffing algorithms
3. 🚀 Implement diff engine for temporal analysis

### For Frontend Integration
1. Load NDJSON artifacts into frontend system
2. Use graph_nodes.ndjson for node visualization
3. Use graph_edges.ndjson for edge visualization
4. Use graph_snapshots.ndjson for temporal animation
5. Use graph_state.ndjson for summary metrics

---

## Support Resources

| Resource | Location | Purpose |
|----------|----------|---------|
| **Comprehensive Guide** | LAYER4_GRAPH_STATE.md | Full documentation on all models, functions, metrics |
| **Layer 5 Guidance** | LAYER5_PREPARATION.md | Architectural guidance for diff engine |
| **Integration Summary** | LAYER4_SURGICAL_INTEGRATION.md | What was done and verification results |
| **Quick Start** | This file | Getting started and common tasks |
| **Source Code** | behavior/graph_*.py | Implementation details |

---

## Summary

Layer 4 is now operational and generating:

✅ **104 graph nodes** representing hosts in the network
✅ **201 graph edges** representing relationships
✅ **262 temporal snapshots** showing topology evolution
✅ **Complete graph state** with metrics and metadata

All data is **deterministically replayed** and **replay-safe** for future analysis.

Ready for Layer 5: Temporal Diff Engine development! 🚀
