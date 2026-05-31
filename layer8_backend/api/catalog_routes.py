from __future__ import annotations

from layer8_backend.services import ReplayService


def build_catalog_router(service: ReplayService | None = None):
    try:
        from fastapi import APIRouter, HTTPException
    except ImportError as exc:
        raise RuntimeError("FastAPI is required to build catalog API routes") from exc

    service = service or ReplayService()
    router = APIRouter()

    @router.get("/api/chapters")
    def chapters():
        return service.chapters()

    @router.get("/api/events")
    def events():
        return service.events()

    @router.get("/api/narratives")
    def narratives():
        return service.narratives()

    @router.get("/api/hosts/{ip}")
    def host_details(ip: str):
        try:
            return service.host(ip)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/api/phases")
    def phases():
        return service.phases()

    return router
