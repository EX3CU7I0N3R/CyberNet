from __future__ import annotations

import json
from typing import Iterable


def export_ndjson(objects: Iterable, output_file: str) -> None:
    with open(output_file, "w", encoding="utf-8") as stream:
        for obj in objects:
            if hasattr(obj, "model_dump"):
                document = obj.model_dump()
            elif hasattr(obj, "dict"):
                document = obj.dict()
            else:
                document = obj
            stream.write(json.dumps(document) + "\n")
