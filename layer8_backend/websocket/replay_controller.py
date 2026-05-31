from __future__ import annotations

from dataclasses import dataclass

from layer8_backend.services import ReplayService


@dataclass
class ReplayPlaybackState:
    frame: int = 1
    playing: bool = False
    speed: int = 1


class ReplayWebSocketController:
    SUPPORTED_SPEEDS = {1, 2, 4, 8, 16, 32}

    def __init__(self, service: ReplayService):
        self.service = service
        self.state = ReplayPlaybackState()

    def handle(self, message: dict):
        action = message.get("action")
        if action == "play":
            self.state.playing = True
            return self._payload(include_frame=True)
        if action == "pause":
            self.state.playing = False
            return self._payload()
        if action == "seek":
            frame = int(message.get("frame", self.state.frame))
            self.state.frame = max(frame, 1)
            return self._payload(include_frame=True)
        if action == "speed":
            speed = int(message.get("value", self.state.speed))
            if speed not in self.SUPPORTED_SPEEDS:
                raise ValueError(f"Unsupported replay speed: {speed}")
            self.state.speed = speed
            return self._payload(include_frame=True)
        raise ValueError(f"Unsupported replay action: {action}")

    def _payload(self, include_frame: bool = False):
        payload = {
            "playing": self.state.playing,
            "frame": self.state.frame,
            "speed": self.state.speed,
        }
        if include_frame:
            payload["replay_frame"] = self.service.get_frame(self.state.frame).model_dump()
        return payload
