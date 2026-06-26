"""Creates, looks up, and reaps rooms.

In-memory for the MVP. Game logic never touches this dict directly — swapping to
a Redis-backed store later only changes this file.
"""

from __future__ import annotations

import asyncio
import random
import string
import time

from ..config import Settings
from ..services.image_gen import build_image_generator
from ..services.judge import build_judge
from .room import Room

_CODE_ALPHABET = string.ascii_uppercase + string.digits


class RoomManager:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.rooms: dict[str, Room] = {}
        self._sweeper: asyncio.Task | None = None

    def _new_code(self) -> str:
        while True:
            code = "".join(random.choices(_CODE_ALPHABET, k=4))
            if code not in self.rooms:
                return code

    def create_room(self) -> Room:
        s = self._settings
        room = Room(
            code=self._new_code(),
            generator=build_image_generator(s.image_provider, fal_key=s.fal_key),
            judge=build_judge(s.judge, anthropic_api_key=s.anthropic_api_key, model=s.judge_model),
            total_rounds=s.total_rounds,
            round_seconds=s.round_seconds,
            max_result_concurrency=s.max_result_concurrency,
        )
        self.rooms[room.code] = room
        return room

    def get_room(self, code: str) -> Room | None:
        return self.rooms.get(code.upper())

    # -- lifecycle ----------------------------------------------------------
    def start_sweeper(self) -> None:
        if self._sweeper is None:
            self._sweeper = asyncio.create_task(self._sweep_loop())

    async def stop_sweeper(self) -> None:
        if self._sweeper is not None:
            self._sweeper.cancel()
            self._sweeper = None

    async def _sweep_loop(self) -> None:
        ttl = self._settings.empty_room_ttl_seconds
        try:
            while True:
                await asyncio.sleep(30)
                now = time.time()
                stale = [
                    code
                    for code, room in self.rooms.items()
                    if room.is_empty() and now - room.last_active > ttl
                ]
                for code in stale:
                    self.rooms.pop(code, None)
        except asyncio.CancelledError:
            pass
