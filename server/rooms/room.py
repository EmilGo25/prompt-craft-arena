"""A single game room: roster, image store, and the async round loop.

The Room is server-authoritative — it owns the phase machine, the timer, and
scoring. Clients only join, start, and submit prompts; everything else is driven
here and broadcast out.
"""

from __future__ import annotations

import asyncio
import math
import time
import uuid

from ..history.summary import (
    GameRecorder,
    GameSummary,
    ParticipantSnapshot,
    ResultSnapshot,
    RoundSnapshot,
)
from ..realtime import protocol as p
from ..realtime.connection import Connection
from ..services.image_gen import GeneratedImage, ImageGenerator
from ..services.judge import Judge, JudgeInput
from ..services.scoring import compose_score
from ..services.seed_prompts import (
    TargetPromptGenerator,
    difficulty_for_round,
)
from .state import (
    GameState,
    Phase,
    Player,
    RoundResult,
    Submission,
    round_winner,
    standings,
)


def _redact_breakdown(result: p.ResultView) -> p.ResultView:
    """A copy of a result with the private scoring breakdown stripped — used for
    everyone except the result's owner. Keeps image, prompt, and final score."""
    return result.model_copy(
        update={"similarity": None, "speed_bonus": None, "rationale": None, "dimensions": None}
    )


class Room:
    def __init__(
        self,
        code: str,
        *,
        generator: ImageGenerator,
        judge: Judge,
        total_rounds: int,
        round_seconds: int,
        max_result_concurrency: int = 4,
        target_difficulty: str = "medium",
        recorder: GameRecorder | None = None,
        leaderboard=None,
        image_retention_seconds: int = 300,
        objective_pool=None,
        metrics=None,
    ) -> None:
        self.code = code
        self.state = GameState(total_rounds=total_rounds, round_seconds=round_seconds)
        self._generator = generator
        self._judge = judge
        self._concurrency = max_result_concurrency
        self._difficulty = target_difficulty
        self._target_prompts = TargetPromptGenerator()
        self._recorder = recorder
        self._leaderboard = leaderboard
        self._image_retention_seconds = image_retention_seconds
        self._objective_pool = objective_pool
        self._metrics = metrics

        self._connections: dict[str, Connection] = {}
        self._images: dict[str, GeneratedImage] = {}
        self._round_history: list[RoundSnapshot] = []
        self._submission_event = asyncio.Event()
        self._game_task: asyncio.Task | None = None
        self._sem = asyncio.Semaphore(max_result_concurrency)
        self._round_start_mono: float = 0.0
        self._inflight: list[asyncio.Task] = []
        self._image_cleanup_task: asyncio.Task | None = None
        self.last_active = time.time()

    # -- roster / connections ----------------------------------------------
    async def connect(
        self,
        name: str,
        connection: Connection,
        *,
        user_id: str | None = None,
        picture_url: str | None = None,
    ) -> str:
        player_id = uuid.uuid4().hex[:8]
        player = Player(id=player_id, name=name, user_id=user_id, picture_url=picture_url)
        self.state.add_player(player)
        self._connections[player_id] = connection
        self.last_active = time.time()

        await connection.send(p.Welcome(player_id=player_id, room_code=self.code))
        await connection.send(self._room_state())
        await self._broadcast(self._room_state(), exclude=player_id)
        return player_id

    async def disconnect(self, player_id: str) -> None:
        self._connections.pop(player_id, None)
        player = self.state.players.get(player_id)
        if player:
            player.connected = False
        self.last_active = time.time()
        # If everyone is gone mid-prompt, let the loop notice via the event.
        self._submission_event.set()
        await self._broadcast(self._room_state())

    def is_empty(self) -> bool:
        return not self._connections

    # -- inbound messages ---------------------------------------------------
    async def handle_message(self, player_id: str, message: p.ClientMessage) -> None:
        self.last_active = time.time()
        match message:
            case p.Ping():
                await self._send(player_id, p.Pong())
            case p.StartGame():
                await self._handle_start(player_id)
            case p.SubmitPrompt():
                await self._handle_submit(player_id, message.prompt, message.lang)
            case p.PlayAgain():
                await self._handle_play_again(player_id)

    async def _handle_start(self, player_id: str) -> None:
        if self.state.host_id() != player_id:
            await self._send(player_id, p.ErrorMessage(detail="Only the host can start the game."))
            return
        if self.state.phase != Phase.LOBBY:
            await self._send(player_id, p.ErrorMessage(detail="Game already in progress."))
            return
        if self._metrics is not None:
            self._metrics.inc("games_started_total")  # demand signal for pool sizing
        self._game_task = asyncio.create_task(self._run_game())

    async def _handle_submit(self, player_id: str, prompt: str, lang: str = "en") -> None:
        rnd = self.state.current_round
        if self.state.phase != Phase.PROMPTING or rnd is None:
            await self._send(player_id, p.ErrorMessage(detail="Not accepting prompts right now."))
            return
        if player_id in rnd.submissions:
            await self._send(player_id, p.ErrorMessage(detail="You already submitted this round."))
            return

        # Fraction of the round's time already elapsed: 0 = instant, 1 = buzzer.
        elapsed = asyncio.get_event_loop().time() - self._round_start_mono
        fraction = elapsed / max(1, self.state.round_seconds)
        submission = Submission(
            player_id=player_id, prompt=prompt, submit_fraction=fraction, lang=lang
        )
        rnd.submissions[player_id] = submission

        # Generate + judge this player's image now, in the background. The result
        # is NOT revealed until the round ends (revealing early enables copying).
        self._inflight.append(asyncio.create_task(self._process_submission(rnd, submission)))

        await self._send(player_id, p.PromptAccepted())
        await self._broadcast(
            p.SubmissionStatus(
                submitted_player_ids=list(rnd.submissions.keys()),
                total=len(self.state.connected_players()),
            )
        )
        self._submission_event.set()

    async def _handle_play_again(self, player_id: str) -> None:
        if self.state.host_id() != player_id:
            return
        if self.state.phase != Phase.GAME_OVER:
            return
        # A new game is starting before the old one's images aged out: cancel the
        # pending deletion so it can't fire mid-game and wipe fresh images.
        self._cancel_image_cleanup()
        for pl in self.state.players.values():
            pl.score = 0
        self.state.phase = Phase.LOBBY
        self.state.round_num = 0
        self.state.current_round = None
        self.state.deadline_ts = None
        self._images.clear()
        self._round_history.clear()
        await self._broadcast(self._room_state())

    # -- the game loop ------------------------------------------------------
    async def _run_game(self) -> None:
        for round_num in range(1, self.state.total_rounds + 1):
            self.state.round_num = round_num
            if not self.state.connected_players():
                break
            await self._generate_target(round_num)
            await self._prompting_phase()
            await self._scoring_phase()
            await self._reveal_phase(round_num)

        self.state.phase = Phase.GAME_OVER
        await self._broadcast(self._phase_changed())
        ranked = standings(self.state)
        await self._broadcast(
            p.GameOver(
                standings=self._player_views(),
                winner_id=ranked[0].id if ranked else None,
            )
        )
        self._record_leaderboard(ranked)
        await self._record_game(ranked)
        # Players linger on the game-over recap (which still renders every round's
        # images), so we can't free them yet. Delete after a grace window.
        self._schedule_image_cleanup()

    def _record_leaderboard(self, ranked: list[Player]) -> None:
        """Fold this game into the global leaderboard (all players, guests too)."""
        if self._leaderboard is None or not self._round_history:
            return
        try:
            self._leaderboard.record_game(
                [(pl.name, pl.score) for pl in ranked],
                rounds_played=len(self._round_history),
            )
        except Exception:  # noqa: BLE001 - never let bookkeeping break a game
            pass

    async def _record_game(self, ranked: list[Player]) -> None:
        if self._recorder is None or not self._round_history:
            return
        participants = [
            ParticipantSnapshot(
                player_id=pl.id,
                user_id=pl.user_id,
                display_name=pl.name,
                final_score=pl.score,
                placement=i + 1,
            )
            for i, pl in enumerate(ranked)
        ]
        summary = GameSummary(
            code=self.code,
            total_rounds=self.state.total_rounds,
            round_seconds=self.state.round_seconds,
            winner_name=ranked[0].name if ranked else None,
            participants=participants,
            rounds=self._round_history,
        )
        if not summary.has_authenticated_participant():
            return  # nothing to attribute; skip to avoid clutter
        try:
            await self._recorder.record(summary)
        except Exception:  # noqa: BLE001 - persistence must never break a game
            pass

    def _snapshot_round(self, round_num: int, rnd: RoundResult) -> RoundSnapshot:
        target = self._images[rnd.target_image_id]
        results: list[ResultSnapshot] = []
        for pid, sub in rnd.submissions.items():
            player = self.state.players.get(pid)
            image = self._images.get(sub.image_id) if sub.image_id else None
            b = sub.breakdown
            results.append(
                ResultSnapshot(
                    player_id=pid,
                    user_id=player.user_id if player else None,
                    display_name=player.name if player else pid,
                    prompt=sub.prompt,
                    score=b.final if b else 0,
                    rationale=b.rationale if b else "",
                    image_bytes=image.image_bytes if image else None,
                    content_type=image.content_type if image else "image/png",
                )
            )
        return RoundSnapshot(
            round_num=round_num,
            target_image_bytes=target.image_bytes,
            target_content_type=target.content_type,
            results=results,
        )

    async def _generate_target(self, round_num: int) -> None:
        self.state.phase = Phase.GENERATING_TARGET
        await self._broadcast(self._phase_changed())
        difficulty = (
            difficulty_for_round(round_num, self.state.total_rounds)
            if self._difficulty == "ramp"
            else self._difficulty
        )
        # Take a pre-generated target off the shelf if one is ready (instant);
        # otherwise fall back to drawing it live — never worse than before.
        image = self._objective_pool.acquire(difficulty) if self._objective_pool else None
        if image is None:
            seed_prompt = self._target_prompts.generate(difficulty)
            image = await self._generator.generate(seed_prompt)
        target_id = self._store_image(image)
        self.state.current_round = RoundResult(target_image_id=target_id)
        await self._broadcast(p.TargetReady(image_id=target_id, round_num=round_num))

    async def _prompting_phase(self) -> None:
        self.state.phase = Phase.PROMPTING
        self._submission_event.clear()
        self._inflight = []
        loop = asyncio.get_event_loop()
        self._round_start_mono = loop.time()
        mono_deadline = self._round_start_mono + self.state.round_seconds
        wall_deadline = time.time() + self.state.round_seconds
        self.state.deadline_ts = wall_deadline
        await self._broadcast(self._phase_changed())

        while True:
            remaining = mono_deadline - loop.time()
            if remaining <= 0 or self.state.all_connected_submitted():
                break
            await self._broadcast(
                p.Timer(seconds_left=math.ceil(remaining), deadline_ts=wall_deadline)
            )
            try:
                await asyncio.wait_for(
                    self._submission_event.wait(), timeout=min(1.0, remaining)
                )
            except asyncio.TimeoutError:
                pass
            self._submission_event.clear()

    async def _process_submission(self, rnd: RoundResult, submission: Submission) -> None:
        """Generate the player's image and judge it vs the target, then compose
        the final score (similarity + speed bonus). Runs in the background the
        moment a prompt is submitted; nothing here is broadcast (anti-cheat)."""
        async with self._sem:
            try:
                image = await self._generator.generate(submission.prompt)
                submission.image_id = self._store_image(image)
                target = self._images[rnd.target_image_id]
                verdict = await self._judge.judge_one(
                    target.image_bytes,
                    JudgeInput(
                        player_id=submission.player_id,
                        player_name=self._name_of(submission.player_id),
                        prompt=submission.prompt,
                        image_bytes=image.image_bytes,
                        content_type=image.content_type,
                    ),
                    target_content_type=target.content_type,
                    language=submission.lang,
                )
                submission.breakdown = compose_score(
                    verdict.score,
                    submission.submit_fraction,
                    verdict.rationale,
                    verdict.dimensions,
                )
            except Exception:  # noqa: BLE001 - one bad submission shouldn't sink the round
                submission.breakdown = compose_score(
                    0, submission.submit_fraction, "(could not generate or score this image)", {}
                )

    async def _scoring_phase(self) -> None:
        """'Waiting for score': hold here until every submitted image has been
        generated and judged, then fold the results into cumulative scores."""
        self.state.phase = Phase.SCORING
        await self._broadcast(self._phase_changed())
        if self._inflight:
            await asyncio.gather(*self._inflight, return_exceptions=True)

        rnd = self.state.current_round
        assert rnd is not None
        scores: dict[str, int] = {pid: 0 for pid in self.state.players}
        for pid, sub in rnd.submissions.items():
            if sub.breakdown is not None:
                scores[pid] = sub.breakdown.final
        self.state.apply_scores(scores)

    async def _reveal_phase(self, round_num: int) -> None:
        self.state.phase = Phase.REVEAL
        rnd = self.state.current_round
        assert rnd is not None
        results: list[p.ResultView] = []
        for pid, sub in rnd.submissions.items():
            b = sub.breakdown
            results.append(
                p.ResultView(
                    player_id=pid,
                    player_name=self._name_of(pid),
                    prompt=sub.prompt,
                    image_id=sub.image_id,
                    score=b.final if b else 0,
                    similarity=b.similarity if b else None,
                    speed_bonus=b.speed_bonus if b else None,
                    rationale=b.rationale if b else None,
                    dimensions=b.dimensions if b else None,
                )
            )
        results.sort(key=lambda r: -(r.score or 0))
        self._round_history.append(self._snapshot_round(round_num, rnd))
        await self._broadcast(self._phase_changed())

        # The scoring breakdown is private: each player receives the full
        # similarity / speed / dimension / rationale detail only for their OWN
        # result. Everyone else's result carries just image, prompt, and the
        # final score. (Sent per-recipient so it can't be inspected on the wire.)
        winner_id = round_winner(rnd)
        standings = self._player_views()
        for recipient_id, conn in list(self._connections.items()):
            tailored = [r if r.player_id == recipient_id else _redact_breakdown(r) for r in results]
            await conn.send(
                p.RoundReveal(
                    round_num=round_num,
                    target_image_id=rnd.target_image_id,
                    results=tailored,
                    winner_id=winner_id,
                    standings=standings,
                )
            )
        await asyncio.sleep(0)  # yield; the UI controls dwell time on reveal

    # -- image store --------------------------------------------------------
    def _store_image(self, image: GeneratedImage) -> str:
        image_id = uuid.uuid4().hex
        self._images[image_id] = image
        return image_id

    def get_image(self, image_id: str) -> GeneratedImage | None:
        return self._images.get(image_id)

    # -- image retention / cleanup -----------------------------------------
    def _schedule_image_cleanup(self) -> None:
        """Free this game's images after the retention window. The game-over
        recap keeps rendering them, so deletion is deferred, not immediate."""
        self._cancel_image_cleanup()
        self._image_cleanup_task = asyncio.create_task(self._cleanup_images_later())

    def _cancel_image_cleanup(self) -> None:
        task = self._image_cleanup_task
        self._image_cleanup_task = None
        if task is not None and not task.done():
            task.cancel()

    async def _cleanup_images_later(self) -> None:
        try:
            await asyncio.sleep(self._image_retention_seconds)
        except asyncio.CancelledError:
            return
        # Drop every image (targets + submissions) and the snapshots that hold
        # copies of their bytes, so a finished game stops occupying memory.
        self._images.clear()
        self._round_history.clear()
        self._image_cleanup_task = None

    def _name_of(self, player_id: str) -> str:
        player = self.state.players.get(player_id)
        return player.name if player else player_id

    # -- outbound helpers ---------------------------------------------------
    async def _broadcast(self, message, *, exclude: str | None = None) -> None:
        for pid, conn in list(self._connections.items()):
            if pid == exclude:
                continue
            await conn.send(message)

    async def _send(self, player_id: str, message) -> None:
        conn = self._connections.get(player_id)
        if conn is not None:
            await conn.send(message)

    def _player_views(self) -> list[p.PlayerView]:
        return [
            p.PlayerView(
                id=pl.id,
                name=pl.name,
                score=pl.score,
                connected=pl.connected,
                is_host=pl.is_host,
                picture_url=pl.picture_url,
            )
            for pl in standings(self.state)
        ]

    def _room_state(self) -> p.RoomState:
        return p.RoomState(
            phase=self.state.phase.value,
            round_num=self.state.round_num,
            total_rounds=self.state.total_rounds,
            players=self._player_views(),
        )

    def _phase_changed(self) -> p.PhaseChanged:
        return p.PhaseChanged(phase=self.state.phase.value, round_num=self.state.round_num)
