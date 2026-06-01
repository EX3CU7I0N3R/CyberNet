# PCAPModels Architecture

## Overview

PCAPModels is a behavioral network telemetry pipeline that ingests PCAP files and produces an interactive replay console with behavioral analysis, investigation narratives, and tactical intelligence.

The architecture is organized into layers, each responsible for progressive enrichment and analysis:

## Layer Structure

### Layers 1-4: Packet Normalization & Graph Foundation
- **Ingestion**: Raw PCAP parsing via pyshark/scapy
- **Normalization**: Standardized packet representation
- **Flow Aggregation**: Temporal flow models with host/port associations
- **Graph Building**: Host and relationship modeling with community detection
- **State Management**: Temporal snapshots and consistency audits

### Layer 5: Hypotheses & Investigation Candidates
- Attack hypothesis generation based on flow patterns
- Confidence scoring with explainable reasoning
- Destination rarity and exclusivity analysis
- Investigation candidate ranking and priority assessment

### Layer 6: Narratives & Assessments
- Analyst-facing narrative generation
- Evidence summarization and chain building
- Confidence explanations and recommendation generation
- Readiness validation and quality metrics

### Layer 7: Timeline & Replay Artifacts
- Timeline event generation and filtering
- Activity phase detection and segmentation
- Replay frame construction for animated visualization
- Major chapter identification for narrative structure

### Layer 7.5: Chapter Management
- Chapter index generation
- Replay frame grouping and navigation

### Layer 8A/8B: Backend API & Frontend Integration
- FastAPI replay server with WebSocket support
- Context API for hosts, relationships, candidates, hypotheses
- Stitch-derived frontend integration
- Real-time replay controls and seeking

## Directory Structure

```
ingestion/           Packet parsing and enrichment
behavior/            Host/relationship models, graph building
layer5/              Hypotheses, confidence, candidates
layer6/              Narratives, assessments
layer7/              Events, phases, replay frames
layer8_backend/      FastAPI server, APIs, WebSocket
frontend/            HTML/CSS/JS replay console
output/              Generated artifacts (NDJSON, JSON, CSV)
tests/               Test suites for each layer
```

## Key Modules

### Ingestion
- `parse.py`: PCAP parsing via pyshark
- `protocol_enrichment.py`: Service/protocol decoration

### Behavior
- `graph_builder.py`: Host graph construction
- `graph_state.py`: Temporal graph snapshots
- `host_profiles.py`: Host behavior models
- `host_risk.py`: Risk assessment
- `roles.py`: Role classification
- `relationships.py`: Host relationship tracking
- `community_classifier.py`: Community detection

### Layer 5
- `hypotheses.py`: Hypothesis generation
- `confidence_explainer.py`: Confidence reasoning
- `investigation_planner.py`: Candidate ranking

### Layer 6
- `reasoning_engine.py`: Evidence chain reasoning
- `narrative_engine/`: Narrative generation
- `exports/`: Output artifact generation

### Layer 7
- `event_engine/`: Timeline event generation
- `phase_engine/`: Activity phase detection
- `replay_engine/`: Replay frame generation
- `chapter_engine/`: Chapter identification

### Layer 8
- `api/app.py`: FastAPI application
- `api/replay_routes.py`: Replay streaming
- `api/catalog_routes.py`: Artifact catalog
- `api/pcap_routes.py`: PCAP selection and analysis
- `services/`: Business logic for APIs
- `websocket/`: WebSocket command channel
- `cache/`: Replay artifact caching
- `providers/`: Data providers

## Output Artifacts

Generated artifacts are written to `output/`:

### Normalized & Flow Artifacts
- `normalized_packets.ndjson`: Standardized packets
- `flows.ndjson`: Unaggregated flows
- `enriched_flows.ndjson`: Flows with service/protocol info

### Behavioral Models
- `host_profiles.ndjson`: Host behavior summaries
- `relationships.ndjson`: Host relationships
- `graph_nodes.ndjson`: Graph node data
- `graph_edges.ndjson`: Graph edge data
- `graph_state.ndjson`: Full graph snapshots
- `graph_snapshots.ndjson`: Temporal graph states

### Layer 5 Analysis
- `layer5_hypotheses.ndjson`: Attack hypotheses
- `layer5_investigation_candidates.ndjson`: Candidates
- `hypothesis_validation.json`: Quality metrics

### Layer 6 Analysis
- `investigation_narratives.ndjson`: Executive narratives
- `layer6_readiness.json`: Readiness assessment

### Layer 7 Artifacts
- `timeline_events.ndjson`: Timeline events
- `activity_phases.ndjson`: Detected phases
- `replay_frames.ndjson`: Replay animation frames
- `replay_index.json`: Frame index for seeking
- `host_timelines.ndjson`: Per-host event timelines

### Layer 7.5 Artifacts
- `major_chapters.ndjson`: Chapter definitions
- `chapter_index.json`: Chapter navigation index

### Validation & Audit
- `community_audit.csv`: Community distribution audit
- `graph_consistency.json`: Graph consistency metrics
- `role_consistency_report.json`: Role classification audit
- `snapshot_quality.json`: Snapshot quality metrics

## API Endpoints

### Replay API
- `POST /api/replay/session`: Create replay session
- `GET /api/replay/frame/{id}`: Fetch frame
- `GET /api/replay/seek?time=...`: Seek to timestamp
- `GET /api/replay/chapter/{id}`: Jump to chapter
- `WS /ws/replay`: WebSocket replay channel

### Context API
- `POST /api/pcap/select`: Upload and analyze PCAP
- `GET /api/summary`: Capture summary
- `GET /api/hosts`: Ranked hosts
- `GET /api/hosts/{ip}`: Host details and timeline
- `GET /api/hypotheses`: Layer 5 hypotheses
- `GET /api/candidates`: Investigation candidates
- `GET /api/relationships?host=...`: Host relationships
- `GET /api/destinations`: Destination intelligence
- `GET /api/community`: Community audit
- `GET /api/artifacts/health`: Validation status
- `GET /api/events`: Timeline events
- `GET /api/chapters`: Major chapters
- `GET /api/narratives`: Narratives
- `GET /api/phases`: Activity phases

## Frontend Pages

| Page | Route | Purpose |
|---|---|---|
| Investigation Analysis | `/` | 3D replay workspace, PCAP selection, playback controls |
| Timeline Summary | `/frontend/timeline.html` | Capture summary, chapter rail, event stream |
| Host Behaviour | `/frontend/hosts.html` | Host ranking, profiles, evidence, destinations |
| Reports | `/frontend/reports.html` | Executive narrative, findings, confidence |

## Development Workflow

1. **Setup**: Create `.venv`, install dependencies from `requirements.txt`
2. **Analysis**: Run `main.py` with a PCAP or use the UI
3. **Testing**: Run test suites for each layer
4. **Validation**: Use stabilization audit to verify layer outputs

## Key Design Patterns

- **NDJSON Streaming**: Large outputs use newline-delimited JSON for memory efficiency
- **Temporal Snapshots**: Graph state preserved at key timestamps for replay
- **Confidence Explainability**: All findings include reasoning chains
- **Frontend DTO Pattern**: Browser never reads raw NDJSON; backend serves clean DTOs via APIs
- **Community Detection**: Behavioral clustering identifies related hosts
- **Role-Based Classification**: Hosts classified into templates (client, server, relay, etc.)
