"""A thin per-player connection abstraction.

The Room talks to ``Connection`` objects, never to FastAPI's WebSocket directly,
so the game logic is transport-agnostic and easy to drive from tests with a fake
connection.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class Connection(Protocol):
    async def send(self, message: BaseModel) -> None:
        ...


class WebSocketConnection:
    """Wraps a FastAPI/Starlette WebSocket. Send failures are swallowed; the
    room's disconnect handling drives cleanup."""

    def __init__(self, websocket) -> None:
        self._ws = websocket

    async def send(self, message: BaseModel) -> None:
        try:
            await self._ws.send_text(message.model_dump_json())
        except Exception:  # noqa: BLE001 - a dead socket is handled on the recv side
            pass


class CollectingConnection:
    """Test double: records every message sent to a player."""

    def __init__(self) -> None:
        self.sent: list[BaseModel] = []

    async def send(self, message: BaseModel) -> None:
        self.sent.append(message)
