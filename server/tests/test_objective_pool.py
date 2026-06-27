"""The pre-generated objective pool: fills itself, serves hits, respects the
ceiling, and a Room takes its target off the shelf when one is ready."""

import asyncio

import pytest

from server.metrics import Metrics
from server.realtime import protocol as p
from server.realtime.connection import CollectingConnection
from server.rooms.room import Room
from server.rooms.state import Phase
from server.services.image_gen import StubImageGenerator
from server.services.judge import RandomJudge
from server.services.objective_pool import ObjectivePool


async def _wait_for(predicate, timeout=5.0):
    loop = asyncio.get_event_loop()
    end = loop.time() + timeout
    while loop.time() < end:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition not met within timeout")


@pytest.mark.asyncio
async def test_pool_fills_to_target_and_serves_hits():
    pool = ObjectivePool(
        StubImageGenerator(size=32),
        difficulties=["medium"],
        target_size=4,
        floor=2,
        max_concurrency=4,
        metrics=Metrics(),
    )
    pool.start()
    try:
        # The background worker brings the shelf up to the target.
        await _wait_for(lambda: pool.stats()["medium"]["ready"] >= 4)

        # Each acquire is a hit served instantly from the shelf. The (s, S)
        # watermark holds steady until the ready count falls to the floor (2),
        # then refills back up to the target — this avoids churning one draw per
        # acquire.
        assert pool.acquire("medium") is not None  # 4 -> 3 (above floor: no refill)
        assert pool.acquire("medium") is not None  # 3 -> 2 (at floor: triggers refill)
        assert pool.metrics.get_counter("objective_pool_hit_total", difficulty="medium") == 2

        await _wait_for(lambda: pool.stats()["medium"]["ready"] >= 4)
    finally:
        await pool.stop()


@pytest.mark.asyncio
async def test_pool_miss_is_recorded_when_empty():
    pool = ObjectivePool(
        StubImageGenerator(size=32), difficulties=["hard"], metrics=Metrics()
    )
    # Not started: shelf is empty, so this is a miss (caller draws live).
    assert pool.acquire("hard") is None
    assert pool.metrics.get_counter("objective_pool_miss_total", difficulty="hard") == 1


@pytest.mark.asyncio
async def test_pool_never_exceeds_ceiling():
    pool = ObjectivePool(
        StubImageGenerator(size=32),
        difficulties=["easy"],
        target_size=100,   # asks for far more...
        floor=1,
        max_pool=5,        # ...than the hard ceiling allows
        max_concurrency=4,
        metrics=Metrics(),
    )
    pool.start()
    try:
        await _wait_for(lambda: pool.stats()["easy"]["ready"] >= 5)
        await asyncio.sleep(0.1)  # give the worker a chance to overshoot if buggy
        s = pool.stats()["easy"]
        assert s["ready"] + s["inflight"] <= 5
    finally:
        await pool.stop()


@pytest.mark.asyncio
async def test_room_takes_target_from_pool():
    metrics = Metrics()
    pool = ObjectivePool(
        StubImageGenerator(size=32),
        difficulties=["medium"],
        target_size=3,
        floor=1,
        metrics=metrics,
    )
    pool.start()
    try:
        await _wait_for(lambda: pool.stats()["medium"]["ready"] >= 1)

        room = Room(
            "TEST",
            generator=StubImageGenerator(size=32),
            judge=RandomJudge(),
            total_rounds=1,
            round_seconds=5,
            target_difficulty="medium",
            objective_pool=pool,
            metrics=metrics,
        )
        host_conn = CollectingConnection()
        host_id = await room.connect("Ann", host_conn)
        await room.handle_message(host_id, p.StartGame())
        await _wait_for(lambda: room.state.phase == Phase.GAME_OVER, timeout=8.0)

        # The target came from the shelf (a hit), and the game start was counted.
        assert metrics.get_counter("objective_pool_hit_total", difficulty="medium") >= 1
        assert metrics.get_counter("games_started_total") == 1
    finally:
        await pool.stop()
