from __future__ import annotations

from pathlib import Path


def export_activity_phases(phases, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for phase in phases:
            stream.write(phase.model_dump_json() + "\n")
