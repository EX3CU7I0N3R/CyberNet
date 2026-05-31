from __future__ import annotations

from layer8_backend.services import ReplayService
from layer8_backend.websocket.replay_controller import ReplayWebSocketController


def build_replay_websocket(app, service: ReplayService | None = None):
    service = service or ReplayService()

    @app.websocket("/ws/replay")
    async def replay_socket(websocket):
        controller = ReplayWebSocketController(service)
        await websocket.accept()
        while True:
            message = await websocket.receive_json()
            try:
                await websocket.send_json(controller.handle(message))
            except ValueError as exc:
                await websocket.send_json({"error": str(exc)})

    return replay_socket
