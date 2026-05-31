from __future__ import annotations

from layer8_backend.services import ReplayService


def build_replay_router(service: ReplayService | None = None):
    try:
        from fastapi import APIRouter, HTTPException
    except ImportError as exc:
        raise RuntimeError("FastAPI is required to build replay API routes") from exc

    service = service or ReplayService()
    router = APIRouter()

    @router.post("/api/replay/session")
    def create_session():
        return service.create_session()

    @router.get("/api/replay/frame/{frame_id}")
    def get_frame(frame_id: str):
        try:
            return service.get_frame(frame_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/api/replay/seek")
    def seek(time: str):
        try:
            return service.seek(time)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/api/replay/chapter/{chapter_id}")
    def jump_chapter(chapter_id: str):
        try:
            return service.chapter_jump(chapter_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return router
