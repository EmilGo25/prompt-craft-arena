"""API-layer integration tests via FastAPI TestClient.

Exercises the real ASGI app (routing, request validation, WebSocket protocol
parsing, and the room game loop) end-to-end over HTTP/WS — using the offline
stub image generator + random judge, so it's fast and needs no API keys.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Settings
from server.rooms.manager import RoomManager


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        _env_file=None,
        image_provider="stub",
        judge="random",
        leaderboard_path=str(tmp_path / "lb.json"),
        round_seconds=5,
        total_rounds=1,
    )
    app = create_app(manager=RoomManager(settings))
    with TestClient(app) as c:
        yield c


# --- REST -----------------------------------------------------------------


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_create_room_with_config(client):
    r = client.post("/rooms", json={"rounds": 2, "round_seconds": 15})
    assert r.status_code == 200
    body = r.json()
    assert len(body["code"]) == 4
    assert body["total_rounds"] == 2
    assert body["round_seconds"] == 15


def test_create_room_defaults_when_no_body(client):
    r = client.post("/rooms")
    assert r.status_code == 200
    assert r.json()["total_rounds"] == 1  # from settings


def test_create_room_rejects_out_of_range(client):
    r = client.post("/rooms", json={"rounds": 99})
    assert r.status_code == 422  # pydantic le=10


def test_get_room_exists_and_missing(client):
    code = client.post("/rooms").json()["code"]
    assert client.get(f"/rooms/{code}").json()["exists"] is True
    assert client.get("/rooms/ZZZZ").json()["exists"] is False


def test_missing_image_is_404(client):
    code = client.post("/rooms").json()["code"]
    assert client.get(f"/rooms/{code}/images/nope").status_code == 404
    assert client.get("/rooms/ZZZZ/images/nope").status_code == 404


def test_leaderboard_starts_empty(client):
    assert client.get("/leaderboard").json() == {"entries": []}


# --- WebSocket: full game over the real app -------------------------------


def _drive_single_player_game(ws, max_messages: int = 120) -> dict | None:
    """Play one player through a full game; return the game_over message."""
    submitted_rounds: set[int] = set()
    game_over = None
    for _ in range(max_messages):
        msg = ws.receive_json()
        t = msg["type"]
        if t == "phase_changed" and msg["phase"] == "prompting":
            if msg["round_num"] not in submitted_rounds:
                submitted_rounds.add(msg["round_num"])
                ws.send_json({"type": "submit_prompt", "prompt": "a red fox at sunset"})
        elif t == "game_over":
            game_over = msg
            break
    return game_over


def test_websocket_full_game_reaches_game_over(client):
    code = client.post("/rooms", json={"rounds": 2, "round_seconds": 5}).json()["code"]
    with client.websocket_connect(f"/rooms/{code}/ws?name=Ada") as ws:
        welcome = ws.receive_json()
        assert welcome["type"] == "welcome"
        player_id = welcome["player_id"]
        assert ws.receive_json()["type"] == "room_state"

        ws.send_json({"type": "start_game"})
        game_over = _drive_single_player_game(ws)

    assert game_over is not None, "game never reached game_over"
    assert game_over["winner_id"] == player_id
    assert any(p["id"] == player_id for p in game_over["standings"])


def test_websocket_unknown_room_closed(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/rooms/ZZZZ/ws?name=Ada") as ws:
            ws.receive_json()


def test_game_records_to_leaderboard(client):
    code = client.post("/rooms", json={"rounds": 1, "round_seconds": 5}).json()["code"]
    with client.websocket_connect(f"/rooms/{code}/ws?name=Champ") as ws:
        assert ws.receive_json()["type"] == "welcome"
        ws.receive_json()  # room_state
        ws.send_json({"type": "start_game"})
        assert _drive_single_player_game(ws) is not None

    entries = client.get("/leaderboard").json()["entries"]
    assert any(e["name"] == "Champ" for e in entries)
