"""A lightweight, file-backed global leaderboard.

Ranks players by their **average per-round score** (0–100) across every game they
have finished — a fair metric regardless of how many rounds a game had. Keyed by
display name for now (guests have no account); when authentication lands
(Workstream B) this switches to a stable user id.

Persistence is a single JSON file written atomically. That's plenty for a
single-process MVP; the same surface swaps to SQLite later without touching
callers.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass


@dataclass
class LeaderboardEntry:
    name: str
    avg: int  # average per-round score, 0-100
    best: int  # best single-game per-round average
    games: int


class LeaderboardStore:
    def __init__(self, path: str) -> None:
        self._path = path
        # key (lowercased name) -> {name, points, rounds, games, best}
        self._players: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self._path, encoding="utf-8") as f:
                self._players = json.load(f).get("players", {})
        except (FileNotFoundError, json.JSONDecodeError):
            self._players = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self._path) or ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"players": self._players}, f)
            os.replace(tmp, self._path)  # atomic
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def record_game(self, results: list[tuple[str, int]], rounds_played: int) -> None:
        """Fold one finished game into the board.

        ``results`` is (display_name, cumulative_final_score) per player;
        ``rounds_played`` is how many rounds actually ran.
        """
        if rounds_played <= 0:
            return
        for name, final_score in results:
            display = (name or "Anon").strip() or "Anon"
            key = display.lower()
            e = self._players.setdefault(
                key, {"name": display, "points": 0, "rounds": 0, "games": 0, "best": 0}
            )
            e["name"] = display  # keep latest casing
            e["points"] += int(final_score)
            e["rounds"] += rounds_played
            e["games"] += 1
            game_avg = round(final_score / rounds_played)
            e["best"] = max(e["best"], game_avg)
        self._save()

    def top(self, limit: int = 20) -> list[LeaderboardEntry]:
        entries = [
            LeaderboardEntry(
                name=e["name"],
                avg=round(e["points"] / e["rounds"]) if e["rounds"] else 0,
                best=e["best"],
                games=e["games"],
            )
            for e in self._players.values()
            if e["rounds"] > 0
        ]
        entries.sort(key=lambda x: (-x.avg, -x.games, x.name.lower()))
        return entries[:limit]
