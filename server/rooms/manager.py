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
from ..leaderboard import LeaderboardStore
from ..metrics import Metrics
from ..services.image_gen import build_image_generator
from ..services.judge import build_judge
from ..services.objective_pool import ObjectivePool
from .room import Room

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _clamp(value: int | None, default: int, *, lo: int, hi: int) -> int:
    if value is None:
        return default
    return max(lo, min(hi, value))


class RoomManager:
    def __init__(self, settings: Settings, recorder=None) -> None:
        self._settings = settings
        self._recorder = recorder
        self.leaderboard = LeaderboardStore(settings.leaderboard_path)
        self.rooms: dict[str, Room] = {}
        self._sweeper: asyncio.Task | None = None
        self.metrics = Metrics()
        self.objective_pool = self._build_pool(settings)

    def _build_pool(self, s: Settings) -> ObjectivePool | None:
        if not s.objective_pool_enabled:
            return None
        # Only stock the difficulties games actually draw: a fixed difficulty
        # needs just that one box, while "ramp" walks through all three. This
        # avoids pre-generating (and paying for) images no game would ever use.
        difficulties = None if s.target_difficulty == "ramp" else [s.target_difficulty]
        return ObjectivePool(
            build_image_generator(
                s.image_provider,
                openai_api_key=s.openai_api_key,
                openai_image_model=s.openai_image_model,
                openai_image_size=s.openai_image_size,
                drawthings_api_base=s.drawthings_api_base,
                drawthings_steps=s.drawthings_steps,
                drawthings_size=s.drawthings_size,
            ),
            difficulties=difficulties,
            target_size=s.objective_pool_target,
            floor=s.objective_pool_floor,
            max_pool=s.objective_pool_max,
            max_concurrency=s.objective_pool_concurrency,
            refill_interval=s.objective_pool_refill_interval_seconds,
            metrics=self.metrics,
        )

    def _new_code(self) -> str:
        while True:
            code = "".join(random.choices(_CODE_ALPHABET, k=4))
            if code not in self.rooms:
                return code

    def create_room(
        self, *, rounds: int | None = None, round_seconds: int | None = None
    ) -> Room:
        s = self._settings
        room = Room(
            code=self._new_code(),
            generator=build_image_generator(
                s.image_provider,
                openai_api_key=s.openai_api_key,
                openai_image_model=s.openai_image_model,
                openai_image_size=s.openai_image_size,
                drawthings_api_base=s.drawthings_api_base,
                drawthings_steps=s.drawthings_steps,
                drawthings_size=s.drawthings_size,
            ),
            judge=build_judge(
                s.judge,
                openai_api_key=s.openai_api_key,
                model=s.judge_model,
                ollama_base_url=s.ollama_base_url,
                ollama_model=s.ollama_judge_model,
            ),
            total_rounds=_clamp(rounds, s.total_rounds, lo=1, hi=10),
            round_seconds=_clamp(round_seconds, s.round_seconds, lo=5, hi=300),
            max_result_concurrency=s.max_result_concurrency,
            target_difficulty=s.target_difficulty,
            recorder=self._recorder,
            leaderboard=self.leaderboard,
            image_retention_seconds=s.image_retention_seconds,
            objective_pool=self.objective_pool,
            metrics=self.metrics,
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
