from __future__ import annotations

from pathlib import Path

from layer8_backend.api.catalog_routes import build_catalog_router
from layer8_backend.api.pcap_routes import build_pcap_router
from layer8_backend.api.replay_routes import build_replay_router
from layer8_backend.services import ReplayService
from layer8_backend.websocket.replay_socket import build_replay_websocket


def create_app(artifact_dir: str = "output"):
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise RuntimeError("FastAPI is required to run the Layer 8 backend API") from exc

    service = ReplayService(artifact_dir)
    app = FastAPI(title="PCAPModels Replay Backend", version="8A")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_replay_router(service))
    app.include_router(build_catalog_router(service))
    app.include_router(build_pcap_router(service))
    build_replay_websocket(app, service)
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

    @app.get("/")
    def stitch_console():
        ui_path = Path("frontend") / "index.html"
        return FileResponse(ui_path)

    return app


try:
    app = create_app()
except RuntimeError:
    app = None
