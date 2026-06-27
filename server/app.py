"""FastAPI app: REST for room create/join + image serving, WebSocket for play."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .config import get_settings
from .realtime import protocol as p
from .realtime.connection import WebSocketConnection
from .rooms.manager import RoomManager


class CreateRoomRequest(BaseModel):
    rounds: int | None = Field(default=None, ge=1, le=10)
    round_seconds: int | None = Field(default=None, ge=5, le=300)


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager: RoomManager = app.state.manager
    manager.start_sweeper()
    if manager.objective_pool is not None:
        manager.objective_pool.start()
    yield
    await manager.stop_sweeper()
    if manager.objective_pool is not None:
        await manager.objective_pool.stop()


def create_app(manager: RoomManager | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Prompt-craft Arena", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.manager = manager or RoomManager(settings)

    @app.get("/health")
    async def health() -> dict:
        manager = app.state.manager
        out: dict = {"ok": True, "rooms": len(manager.rooms)}
        if manager.objective_pool is not None:
            out["objective_pool"] = manager.objective_pool.stats()
        return out

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(
            content=app.state.manager.metrics.render(),
            media_type="text/plain; version=0.0.4",
        )

    @app.post("/rooms")
    async def create_room(body: CreateRoomRequest | None = None) -> dict:
        body = body or CreateRoomRequest()
        room = app.state.manager.create_room(
            rounds=body.rounds, round_seconds=body.round_seconds
        )
        return {
            "code": room.code,
            "total_rounds": room.state.total_rounds,
            "round_seconds": room.state.round_seconds,
        }

    @app.get("/leaderboard")
    async def leaderboard(limit: int = 20) -> dict:
        entries = app.state.manager.leaderboard.top(max(1, min(100, limit)))
        return {
            "entries": [
                {"rank": i + 1, "name": e.name, "avg": e.avg, "best": e.best, "games": e.games}
                for i, e in enumerate(entries)
            ]
        }

    @app.get("/rooms/{code}")
    async def get_room(code: str) -> dict:
        room = app.state.manager.get_room(code)
        if room is None:
            return {"exists": False}
        return {
            "exists": True,
            "code": room.code,
            "phase": room.state.phase.value,
            "players": len(room.state.players),
        }

    @app.get("/rooms/{code}/images/{image_id}")
    async def get_image(code: str, image_id: str) -> Response:
        room = app.state.manager.get_room(code)
        if room is None:
            return Response(status_code=404)
        image = room.get_image(image_id)
        if image is None:
            return Response(status_code=404)
        return Response(content=image.image_bytes, media_type=image.content_type)

    @app.websocket("/rooms/{code}/ws")
    async def play(websocket: WebSocket, code: str, name: str = "Player") -> None:
        room = app.state.manager.get_room(code)
        if room is None:
            await websocket.close(code=4404, reason="Room not found")
            return
        await websocket.accept()
        connection = WebSocketConnection(websocket)
        player_id = await room.connect(name[:24] or "Player", connection)
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    message = p.parse_client_message(raw)
                except Exception:
                    await connection.send(p.ErrorMessage(detail="Invalid message."))
                    continue
                await room.handle_message(player_id, message)
        except WebSocketDisconnect:
            pass
        finally:
            await room.disconnect(player_id)

    return app


app = create_app()
