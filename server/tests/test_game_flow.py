"""End-to-end: drive a full game through the Room with stub services.

Uses CollectingConnection (no WebSocket) and the stub image generator + random
judge, so it runs fast and offline. Asserts the room reaches GAME_OVER with
consistent cumulative standings.
"""

import asyncio

import pytest

from server.realtime import protocol as p
from server.realtime.connection import CollectingConnection
from server.rooms.room import Room
from server.rooms.state import Phase
from server.services.image_gen import StubImageGenerator
from server.services.judge import RandomJudge


async def _wait_for(predicate, timeout=5.0):
    loop = asyncio.get_event_loop()
    end = loop.time() + timeout
    while loop.time() < end:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition not met within timeout")


def _last(conn: CollectingConnection, msg_type) -> object | None:
    for m in reversed(conn.sent):
        if isinstance(m, msg_type):
            return m
    return None


@pytest.mark.asyncio
async def test_full_game_reaches_game_over():
    room = Room(
        "TEST",
        generator=StubImageGenerator(size=64),
        judge=RandomJudge(),
        total_rounds=2,
        round_seconds=5,
    )
    host_conn = CollectingConnection()
    guest_conn = CollectingConnection()
    host_id = await room.connect("Ann", host_conn)
    guest_id = await room.connect("Bo", guest_conn)

    # Both players received a Welcome and the lobby roster.
    assert _last(host_conn, p.Welcome) is not None
    assert room.state.host_id() == host_id

    # Host starts the game.
    await room.handle_message(host_id, p.StartGame())

    def reveal_count() -> int:
        return sum(isinstance(m, p.RoundReveal) for m in host_conn.sent)

    for n in range(1, room.state.total_rounds + 1):
        # Wait until prompting opens for round n, then both submit (resolves early).
        await _wait_for(
            lambda n=n: room.state.phase == Phase.PROMPTING and room.state.round_num == n
        )
        await room.handle_message(host_id, p.SubmitPrompt(prompt="a red fox"))
        await room.handle_message(guest_id, p.SubmitPrompt(prompt="a blue whale"))
        # Reveal messages accumulate monotonically — wait for this round's.
        await _wait_for(lambda n=n: reveal_count() >= n)

    await _wait_for(lambda: room.state.phase == Phase.GAME_OVER)

    game_over = _last(host_conn, p.GameOver)
    assert game_over is not None
    assert game_over.winner_id in (host_id, guest_id)

    # Cumulative score equals the sum of both round scores per player.
    reveals = [m for m in host_conn.sent if isinstance(m, p.RoundReveal)]
    assert len(reveals) == 2
    totals = {host_id: 0, guest_id: 0}
    for reveal in reveals:
        for r in reveal.results:
            totals[r.player_id] += r.score
    final = {pv.id: pv.score for pv in game_over.standings}
    assert final == totals

    # Every image referenced in the reveal is fetchable from the room store.
    for reveal in reveals:
        assert room.get_image(reveal.target_image_id) is not None
        for r in reveal.results:
            assert r.image_id is not None
            assert room.get_image(r.image_id) is not None

    # The scoring breakdown is private: host_conn (Ann) gets the full breakdown
    # only for her OWN result; other players' breakdowns are redacted.
    r0 = reveals[0]
    mine = next(r for r in r0.results if r.player_id == host_id)
    assert mine.similarity is not None and mine.speed_bonus is not None
    assert mine.dimensions and set(mine.dimensions) == {
        "subject", "composition", "color", "mood",
    }
    others = [r for r in r0.results if r.player_id != host_id]
    assert others, "expected another player's result in the reveal"
    for o in others:
        assert o.score is not None  # final score stays public (leaderboard)
        assert o.similarity is None and o.speed_bonus is None
        assert o.rationale is None and o.dimensions is None

    # Players passed through the 'waiting for score' (SCORING) phase.
    assert any(
        isinstance(m, p.PhaseChanged) and m.phase == Phase.SCORING.value
        for m in host_conn.sent
    )


async def _play_one_round_to_game_over(room: Room, host_conn: CollectingConnection) -> str:
    """Drive a single-round game to GAME_OVER and return the host's id."""
    host_id = await room.connect("Ann", host_conn)
    await room.handle_message(host_id, p.StartGame())
    await _wait_for(lambda: room.state.phase == Phase.PROMPTING)
    await room.handle_message(host_id, p.SubmitPrompt(prompt="a red fox"))
    await _wait_for(lambda: room.state.phase == Phase.GAME_OVER)
    return host_id


@pytest.mark.asyncio
async def test_images_deleted_after_retention_window():
    room = Room("TEST", generator=StubImageGenerator(size=64), judge=RandomJudge(),
                total_rounds=1, round_seconds=5, image_retention_seconds=0.2)
    host_conn = CollectingConnection()
    await _play_one_round_to_game_over(room, host_conn)

    reveal = _last(host_conn, p.RoundReveal)
    assert reveal is not None
    # Images are still fetchable right after the game ends (recap screen needs them).
    assert room.get_image(reveal.target_image_id) is not None
    assert room._images  # noqa: SLF001 - asserting internal store cleared below

    # After the retention window they're freed.
    await _wait_for(lambda: not room._images, timeout=3.0)  # noqa: SLF001
    assert room.get_image(reveal.target_image_id) is None
    assert room._round_history == []  # noqa: SLF001


@pytest.mark.asyncio
async def test_play_again_cancels_pending_image_cleanup():
    # Long window so the cleanup would NOT fire on its own during the test.
    room = Room("TEST", generator=StubImageGenerator(size=64), judge=RandomJudge(),
                total_rounds=1, round_seconds=5, image_retention_seconds=60)
    host_conn = CollectingConnection()
    host_id = await _play_one_round_to_game_over(room, host_conn)
    assert room._image_cleanup_task is not None  # noqa: SLF001

    await room.handle_message(host_id, p.PlayAgain())
    assert room.state.phase == Phase.LOBBY
    # The pending deletion is cancelled so it can't wipe the next game's images.
    assert room._image_cleanup_task is None  # noqa: SLF001
    assert room._images == {}  # noqa: SLF001 - play_again also clears the old images


@pytest.mark.asyncio
async def test_non_host_cannot_start():
    room = Room("TEST", generator=StubImageGenerator(size=64), judge=RandomJudge(),
                total_rounds=1, round_seconds=3)
    host_conn = CollectingConnection()
    guest_conn = CollectingConnection()
    await room.connect("Ann", host_conn)
    guest_id = await room.connect("Bo", guest_conn)

    await room.handle_message(guest_id, p.StartGame())
    assert room.state.phase == Phase.LOBBY
    assert _last(guest_conn, p.ErrorMessage) is not None


@pytest.mark.asyncio
async def test_timer_expiry_resolves_round_without_submissions():
    room = Room("TEST", generator=StubImageGenerator(size=64), judge=RandomJudge(),
                total_rounds=1, round_seconds=1)
    host_conn = CollectingConnection()
    host_id = await room.connect("Ann", host_conn)
    await room.handle_message(host_id, p.StartGame())
    # No submissions; the 1s timer must still carry the game to GAME_OVER.
    await _wait_for(lambda: room.state.phase == Phase.GAME_OVER, timeout=8.0)
    assert room.state.players[host_id].score == 0
