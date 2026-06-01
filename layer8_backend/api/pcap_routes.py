from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from layer8_backend.services import ReplayService


def build_pcap_router(service: ReplayService):
    router = APIRouter()

    @router.post("/api/pcap/select")
    async def select_pcap(file: UploadFile = File(...)):
        filename = Path(file.filename or "").name
        if not filename:
            raise HTTPException(status_code=400, detail="No PCAP filename supplied")
        if Path(filename).suffix.lower() not in {".pcap", ".pcapng", ".cap"}:
            raise HTTPException(status_code=400, detail="Unsupported capture file type")

        upload_dir = Path(service.artifact_dir) / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        capture_path = upload_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{filename}"
        capture_path.write_bytes(await file.read())

        command = [sys.executable, "main.py", str(capture_path), "--no-csv"]
        completed = subprocess.run(command, cwd=Path.cwd(), capture_output=True, text=True, timeout=600)
        if completed.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "PCAP analysis failed",
                    "stdout": completed.stdout[-4000:],
                    "stderr": completed.stderr[-4000:],
                },
            )

        service.reload()
        summary = service.summary()
        return {
            "filename": filename,
            "stored_path": str(capture_path),
            "summary": summary.model_dump(),
        }

    return router
