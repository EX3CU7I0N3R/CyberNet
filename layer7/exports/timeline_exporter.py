from __future__ import annotations

from pathlib import Path


def export_timeline_events(events, output_path: str) -> None:
    _write_ndjson(events, output_path)


def _write_ndjson(items, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for item in items:
            stream.write(item.model_dump_json() + "\n")
