# Frontend

Stitch-derived Layer 8 replay console.

Run it through the backend so API calls resolve from the same origin:

```powershell
uvicorn layer8_backend.api.app:app --reload
```

Open:

```text
http://localhost:8000/
```

The frontend consumes Layer 8A DTOs from `/api/...` and does not read Layer 7 NDJSON artifacts directly.

Pages:

- `/` - investigation replay workspace
- `/frontend/timeline.html` - timeline summary
- `/frontend/hosts.html` - host behaviour
- `/frontend/reports.html` - strategic briefing
