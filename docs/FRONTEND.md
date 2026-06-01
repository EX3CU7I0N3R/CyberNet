# Frontend Documentation

## Overview

The PCAPModels frontend is a single-page application for interactive PCAP replay and analysis. It provides 4 main pages served from `frontend/`:

- Investigation Analysis (replay workspace)
- Timeline Summary
- Host Behaviour Analysis
- Reports

The frontend is implemented in plain HTML/CSS/JavaScript with Three.js for 3D visualization.

## Pages

### Investigation Analysis (`index.html`)
The main replay workspace with:
- 3D behavioral graph visualization
- PCAP selection interface
- Replay controls (play, pause, seek, speed)
- Event feed with real-time updates
- Chapter rail for narrative navigation
- Node/relationship inspection panels

**Key Features:**
- Click nodes to inspect host details
- Click edges to inspect relationships
- Primary suspicious destinations are highlighted
- Seek along timeline using the progress bar
- Jump to chapters for guided analysis

### Timeline Summary (`timeline.html`)
Event stream and timeline overview:
- Capture summary cards
- Chapter rail navigation
- Filterable event timeline
- Links to replay seek positions
- High-level activity overview

### Host Behaviour (`hosts.html`)
Host-centric analysis:
- Ranked host list with risk indicators
- Host profile with behavioral summary
- Evidence timeline for each host
- Destination intelligence
- Recommended actions and findings
- Event timeline by host

### Reports (`reports.html`)
Executive-facing analysis:
- Executive narrative summary
- Primary findings and recommendations
- Evidence chain with confidence details
- Copy/export actions
- Analyst confidence explanations

## Top Navigation (Shared)

All pages include a shared navigation bar with:
- **SELECT PCAP**: File picker to upload and analyze a PCAP
- **Notification Icon**: Artifact health status and validation warnings
- **Settings Icon**: Session context, current PCAP info, PCAP re-selection

## Replay Controls

Available in Investigation Analysis:

| Control | Action |
|---|---|
| Play/Pause | Start/stop frame animation |
| First/Last | Jump to first or last frame |
| Speed Selector | Change playback speed (0.5x to 4x) |
| Timeline Seek | Drag to seek to timestamp |
| Chapter Rail | Click chapter segment to jump and inspect |

## Graph Interaction

In the 3D replay workspace:

- **Node Interaction**: Click a host node to open host inspection dialog
- **Edge Interaction**: Click a relationship edge to inspect destination evidence
- **Highlighting**: Primary suspicious destination relationship highlighted when present in frame
- **Pan/Zoom**: Scroll/drag to navigate the 3D space

## Color Scheme

The UI uses the Material Design "Tactical Deep Space" palette:

- **Primary**: `#c3f5ff` (bright cyan)
- **Surface**: `#0d1516` (very dark blue)
- **On-Surface**: `#dce4e5` (light gray)
- **Tertiary**: `#ffeac0` (warm gold accent)
- **Error**: `#ffb4ab` (soft red)

See `frontend/DESIGN.md` for the complete color system.

## API Integration

The frontend consumes backend APIs exclusively. **Never read NDJSON directly from the browser.**

Key endpoints used:

- `/api/replay/frame/{id}`: Get replay frame data
- `/api/replay/seek?time=...`: Seek to timestamp
- `/api/summary`: Get capture summary
- `/api/hosts`: Get host list
- `/api/hosts/{ip}`: Get host details
- `/api/relationships?host=...`: Get relationship data
- `/api/hypotheses`: Get hypotheses
- `/api/candidates`: Get investigation candidates
- `/api/events`: Get timeline events
- `/api/narratives`: Get narratives
- `WS /ws/replay`: WebSocket for replay commands

## Asset Loading

- **Three.js**: Loaded from CDN
- **HTML/CSS**: Single-file per page (no build step)
- **No external dependencies**: Minimal frontend dependencies

## Styling Principles

- **High Contrast**: White text on dark backgrounds for analyst use
- **Minimal Clutter**: Focus on data visualization, not decoration
- **Responsive Controls**: Touch and mouse friendly
- **Accessibility**: Color contrast and keyboard navigation

## Files

```
frontend/
  index.html              Main replay workspace
  timeline.html           Timeline summary
  hosts.html              Host analysis
  reports.html            Executive reports
  DESIGN.md               Color system and design tokens
  README.md               Original frontend notes
```

## Development

To test frontend changes:

1. Start the backend: `uvicorn layer8_backend.api.app:app --host 127.0.0.1 --port 8000`
2. Open `http://localhost:8000/`
3. Select or upload a PCAP
4. Use the UI to verify changes

To debug JavaScript:
- Use browser DevTools (F12)
- Check console for errors
- Inspect network calls to `/api/...` endpoints

## Deployment

The frontend is served directly by the FastAPI backend. No separate build or deployment step is required. Simply place HTML files in the `frontend/` directory and update routes in `layer8_backend.api.app:app`.
