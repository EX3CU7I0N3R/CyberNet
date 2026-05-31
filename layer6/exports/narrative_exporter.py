from __future__ import annotations

from pathlib import Path


def export_narratives(narratives, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for narrative in narratives:
            stream.write(narrative.model_dump_json() + "\n")
