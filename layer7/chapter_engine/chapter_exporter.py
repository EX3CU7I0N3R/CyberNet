from __future__ import annotations

import json
from pathlib import Path


def export_major_chapters(chapters, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for chapter in chapters:
            stream.write(chapter.model_dump_json() + "\n")


def export_chapter_index(chapters, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "chapter_count": len(chapters),
        "chapters": [
            {
                "id": chapter.chapter_id,
                "title": chapter.title,
                "start_time": chapter.start_time,
                "end_time": chapter.end_time,
            }
            for chapter in chapters
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
