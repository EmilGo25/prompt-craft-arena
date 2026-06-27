"""A shelf of pre-generated objective images, kept topped up in the background.

An objective image depends only on a difficulty level — nothing player- or
game-specific — so any pre-generated image is reusable by any game. That turns
"don't make players wait ~15-30s for a live image" into a pure inventory problem:
hold a buffer ("shelf") per difficulty and refill it off the request path.

This is the **reactive** layer: a low/high-watermark (`(s, S)`) top-up sized by a
fixed target per difficulty. When the ready count for a difficulty falls to the
floor, a background worker generates back up to the target, bounded by a
concurrency cap and a hard per-difficulty ceiling (the cost seatbelt).

A **predictive** layer (raising the target ahead of forecasted peaks) layers on
top without touching this class — it just calls :meth:`set_target` over time.

Single server / in-memory for now, matching the rest of the MVP. A multi-instance
deployment would back the shelf with Redis lists; only this file changes.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque

from ..metrics import Metrics
from .image_gen import GeneratedImage, ImageGenerator
from .seed_prompts import Difficulty, TargetPromptGenerator

_DEFAULT_DIFFICULTIES = [d.value for d in Difficulty]


class ObjectivePool:
    def __init__(
        self,
        generator: ImageGenerator,
        prompt_gen: TargetPromptGenerator | None = None,
        *,
        difficulties: list[str] | None = None,
        target_size: int = 8,
        floor: int = 3,
        max_pool: int = 50,
        max_concurrency: int = 4,
        refill_interval: float = 2.0,
        metrics: Metrics | None = None,
    ) -> None:
        self._gen = generator
        self._prompts = prompt_gen or TargetPromptGenerator()
        self._difficulties = difficulties or list(_DEFAULT_DIFFICULTIES)
        self._target = {d: target_size for d in self._difficulties}
        self._floor = floor
        self._max_pool = max_pool
        self._sem = asyncio.Semaphore(max_concurrency)
        self._refill_interval = refill_interval
        self.metrics = metrics or Metrics()

        self._ready: dict[str, deque[GeneratedImage]] = {
            d: deque() for d in self._difficulties
        }
        self._inflight: dict[str, int] = {d: 0 for d in self._difficulties}
        self._task: asyncio.Task | None = None
        self._wake = asyncio.Event()
        self._closed = False
        for d in self._difficulties:
            self._publish_gauges(d)

    # -- take from the shelf (called on the game's request path) ------------
    def acquire(self, difficulty: str) -> GeneratedImage | None:
        """Pop a ready objective for this difficulty, or ``None`` on a miss.

        A miss means the game must draw its target live (the old slow path) — so
        the pool is never worse than not having one. Misses are recorded; their
        rate is the SLI that tells you whether the shelf is deep enough.
        """
        d = str(difficulty)
        q = self._ready.get(d)
        if q:
            image = q.popleft()
            self.metrics.inc("objective_pool_hit_total", difficulty=d)
            self._publish_gauges(d)
            self._wake.set()  # we just consumed; the worker may need to refill
            return image
        self.metrics.inc("objective_pool_miss_total", difficulty=d)
        self._wake.set()
        return None

    # -- predictive hook: adjust the target for a difficulty ----------------
    def set_target(self, difficulty: str, target: int) -> None:
        d = str(difficulty)
        if d not in self._target:
            return
        self._target[d] = max(0, min(self._max_pool, target))
        self._publish_gauges(d)
        self._wake.set()

    def stats(self) -> dict[str, dict[str, int]]:
        return {
            d: {
                "ready": len(self._ready[d]),
                "inflight": self._inflight[d],
                "target": self._target[d],
            }
            for d in self._difficulties
        }

    # -- lifecycle ----------------------------------------------------------
    def start(self) -> None:
        if self._task is None:
            self._closed = False
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._closed = True
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    # -- the background worker ----------------------------------------------
    async def _run(self) -> None:
        try:
            while not self._closed:
                self._replenish_once()
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=self._refill_interval)
                except asyncio.TimeoutError:
                    pass
                self._wake.clear()
        except asyncio.CancelledError:
            pass

    def _replenish_once(self) -> None:
        """(s, S) watermark: when ready+inflight has fallen to the floor, queue
        generations to bring it back up to the target — capped by the ceiling."""
        for d in self._difficulties:
            have = len(self._ready[d]) + self._inflight[d]
            if have <= self._floor:
                ceiling = min(self._target[d], self._max_pool)
                deficit = ceiling - have
                for _ in range(max(0, deficit)):
                    self._inflight[d] += 1
                    asyncio.create_task(self._generate_one(d))
            self._publish_gauges(d)

    async def _generate_one(self, difficulty: str) -> None:
        try:
            async with self._sem:
                if self._closed:
                    return
                prompt = self._prompts.generate(difficulty)
                start = time.monotonic()
                image = await self._gen.generate(prompt)
                elapsed = time.monotonic() - start
            self._ready[difficulty].append(image)
            self.metrics.observe(
                "objective_generation_seconds", elapsed, difficulty=difficulty
            )
            self.metrics.inc("objective_generated_total", difficulty=difficulty)
        except Exception:  # noqa: BLE001 - one failed draw must not kill the worker
            self.metrics.inc("objective_generation_failures_total", difficulty=difficulty)
        finally:
            self._inflight[difficulty] = max(0, self._inflight[difficulty] - 1)
            self._publish_gauges(difficulty)
            self._wake.set()

    def _publish_gauges(self, difficulty: str) -> None:
        self.metrics.set_gauge(
            "objective_pool_ready", len(self._ready[difficulty]), difficulty=difficulty
        )
        self.metrics.set_gauge(
            "objective_pool_inflight", self._inflight[difficulty], difficulty=difficulty
        )
        self.metrics.set_gauge(
            "objective_pool_target", self._target[difficulty], difficulty=difficulty
        )
