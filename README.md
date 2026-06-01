# PCAPModels

PCAPModels is a behavioral network telemetry pipeline and replay console for PCAP investigation.

It parses a capture, builds behavioral host and relationship models, generates investigation hypotheses and narratives, converts the result into replay artifacts, and serves a tactical web frontend for analyst review.

The current workflow is:

1. Start the Layer 8 backend.
2. Open the frontend.
3. Click `SELECT PCAP`.
4. Choose a `.pcap`, `.pcapng`, or `.cap` file.
5. The backend runs the full analysis pipeline and reloads the replay console.

The frontend never reads NDJSON artifacts directly. It consumes backend DTOs from `/api/...`.

## Requirements

- Windows PowerShell
- Python 3.10+
- Wireshark/TShark installed and available on `PATH`
- A local PCAP file

Python dependencies are managed through `requirements.txt`.

```powershell
cd c:\Users\siddh\VSCodeFiles\PCAPModels
python -m venv .
& .\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Important packages:

- `pyshark` for PCAP parsing
- `scapy` for packet tooling
- `pandas` for tabular exports
- `fastapi` and `uvicorn` for the replay backend
- `python-multipart` for browser PCAP uploads

## Start The App

Start the backend:

```powershell
.\Scripts\python.exe -m uvicorn layer8_backend.api.app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://localhost:8000/
```

The first screen should show the tactical replay workspace with a `SELECT PCAP` button in the top navigation.

## Analyze A PCAP From The UI

1. Open `http://localhost:8000/`.
2. Click `SELECT PCAP`.
3. Select a `.pcap`, `.pcapng`, or `.cap` file.
4. Wait for analysis to complete.
5. The replay workspace reloads from the newly generated artifacts.

The upload route stores captures under:

```text
output/uploads/
```

After analysis, the backend reloads its artifact provider so all frontend pages reflect the selected PCAP.

## Frontend Pages

| Page | Route | Purpose |
|---|---|---|
| Investigation Analysis | `/` | 3D replay workspace, PCAP selection, play/pause, seek, event feed, chapter rail, node/relationship inspection |
| Timeline Summary | `/frontend/timeline.html` | Capture summary cards, chapter rail, filterable event stream, replay seek links |
| Host Behaviour | `/frontend/hosts.html` | Ranked host list, host profile, evidence, destination intelligence, event timeline, recommended actions |
| Reports | `/frontend/reports.html` | Executive narrative, primary finding, evidence chain, confidence details, copy/export actions |

The top navigation is shared across all pages.

## Main UI Controls

Top navigation:

- `SELECT PCAP`: opens the file picker and starts backend analysis.
- Notification icon: opens artifact health and validation status.
- Settings icon: opens current replay/session context and allows selecting another PCAP.

Replay controls:

- Play/pause replay frames.
- Jump to first or last frame.
- Change playback speed.
- Seek along the timeline.
- Click chapter segments to jump and inspect chapter context.

Graph inspection:

- Click a node to open host inspection.
- Click an edge to open relationship inspection.
- The primary suspicious destination relationship is highlighted when present in the replay frame.

## Backend API

Replay API:

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/replay/session` | Create replay session metadata |
| `GET` | `/api/replay/frame/{id}` | Fetch a replay frame |
| `GET` | `/api/replay/seek?time=...` | Fetch nearest frame for a timestamp |
| `GET` | `/api/replay/chapter/{id}` | Jump to a chapter start frame |
| `WS` | `/ws/replay` | WebSocket replay command channel |

PCAP selection:

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/pcap/select` | Upload a PCAP, run analysis, reload replay artifacts |

Context API:

| Method | Route | Description |
|---|---|---|
| `GET` | `/api/summary` | Capture totals, top host, primary destination, validation summary |
| `GET` | `/api/hosts` | Ranked hosts with risk, role, candidate status, finding count |
| `GET` | `/api/hosts/{ip}` | Host timeline, events, chapters, risk, role |
| `GET` | `/api/hypotheses` | Layer 5 hypotheses with evidence and confidence explanations |
| `GET` | `/api/candidates` | Investigation candidates with priority explanations and actions |
| `GET` | `/api/relationships?host=...` | Host relationship context and destination evidence |
| `GET` | `/api/destinations` | Ranked destination intelligence |
| `GET` | `/api/community` | Community distribution and node classification audit |
| `GET` | `/api/artifacts/health` | Stabilization and readiness validation status |
| `GET` | `/api/events` | Timeline events |
| `GET` | `/api/chapters` | Major replay chapters |
| `GET` | `/api/narratives` | Investigation narratives |
| `GET` | `/api/phases` | Activity phases |

## Command-Line Analysis

The UI is the preferred workflow now, but the pipeline can still be run directly:

```powershell
.\Scripts\python.exe main.py sample.pcap --no-csv
```

Artifacts are written to:

```text
output/
```

Use `--no-csv` to skip CSV exports. NDJSON export is enabled by default unless `--no-ndjson` is passed.

## Output Artifacts

Important generated artifacts include:

- `normalized_packets.ndjson`
- `flows.ndjson`
- `enriched_flows.ndjson`
- `host_profiles.ndjson`
- `relationships.ndjson`
- `graph_nodes.ndjson`
- `graph_edges.ndjson`
- `graph_state.ndjson`
- `graph_snapshots.ndjson`
- `layer5_hypotheses.ndjson`
- `layer5_investigation_candidates.ndjson`
- `investigation_narratives.ndjson`
- `timeline_events.ndjson`
- `activity_phases.ndjson`
- `host_timelines.ndjson`
- `major_chapters.ndjson`
- `replay_frames.ndjson`
- `replay_index.json`

Stabilization and readiness outputs:

- `community_audit.csv`
- `graph_consistency.json`
- `role_consistency_report.json`
- `hypothesis_validation.json`
- `investigation_candidate_validation.json`
- `snapshot_quality.json`
- `layer6_readiness.json`

## Current Layer Map

- Layers 1-4: packet normalization, flows, host profiles, relationship modeling, graph state, temporal snapshots
- Layer 5: attack hypotheses, confidence hardening, destination rarity/exclusivity, investigation candidates
- Layer 6: analyst narratives, evidence summaries, recommendations
- Layer 7: timeline events, activity phases, replay frames, host timelines
- Layer 7.5: major chapters and chapter index
- Layer 8A/8B: replay backend, context APIs, WebSocket stream, Stitch-derived frontend integration

## Validation

Run the focused Layer 8 backend tests:

```powershell
.\Scripts\python.exe -m unittest tests.test_layer8_backend
```

Run the broader stabilization suite:

```powershell
.\Scripts\python.exe -m unittest tests.test_layer8_backend tests.test_layer75_chapters tests.test_layer7_events tests.test_layer7_phases tests.test_layer7_replay tests.test_layer7_index tests.test_layer6_quality tests.test_layer6_narratives tests.test_layer5_phase1 tests.test_sprint_a_architecture tests.test_stabilization_audit
```

Frontend JavaScript can be syntax-checked by extracting embedded scripts from `frontend/*.html` and running `node --check`. The current frontend is plain HTML/CSS/JS with Three.js loaded from CDN.

## Troubleshooting

If PCAP selection fails immediately:

- Confirm `python-multipart` is installed:

```powershell
.\Scripts\python.exe -c "import multipart; print('ok')"
```

If PCAP parsing fails:

- Confirm Wireshark/TShark is installed.
- Confirm `tshark` is available on `PATH`.
- Try running the CLI path directly:

```powershell
.\Scripts\python.exe main.py sample.pcap --no-csv
```

If the frontend loads old data:

- Select the PCAP again from the UI.
- Confirm the backend returned `200` from `/api/pcap/select`.
- Refresh the browser after the analysis completes.

If port `8000` is already in use:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

Then either stop the owning process or run Uvicorn on another port.

## Project Notes

- The frontend is intentionally single-file HTML per page for now.
- Do not expose raw NDJSON directly to the browser.
- Keep generated artifacts under `output/`.
- Source Stitch template folders are retained separately; the active frontend lives under `frontend/`.
- See `docs/FRONTEND_UX_CONTEXT_PLAN.md` for the UX/context plan.
- See `docs/LAYER8A_STITCH_INTEGRATION.md` for replay API and frontend integration notes.
