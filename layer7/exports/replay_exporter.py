from __future__ import annotations

from pathlib import Path


def export_replay_frames(frames, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for frame in frames:
            stream.write(frame.model_dump_json() + "\n")


def export_replay_index(index, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(index.model_dump_json(indent=2), encoding="utf-8")


def export_host_timelines(host_timelines, output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for host_timeline in host_timelines:
            stream.write(host_timeline.model_dump_json() + "\n")
