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

from ..realtime import protocol as p
from ..realtime.connection import Connection
from ..services.image_gen import GeneratedImage, ImageGenerator, generate_many
from ..services.judge import Judge, JudgeInput
from ..services.seed_prompts import random_seed_prompt
from .state import (
    GameState,
    Phase,
    Player,
    RoundResult,
    Submission,
    round_winner,
    standings,
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
    ) -> None:
        self.code = code
        self.state = GameState(total_rounds=total_rounds, round_seconds=round_seconds)
        self._generator = generator
        self._judge = judge
        self._concurrency = max_result_concurrency

        self._connections: dict[str, Connection] = {}
        self._images: dict[str, GeneratedImage] = {}
        self._submission_event = asyncio.Event()
        self._game_task: asyncio.Task | None = None
        self.last_active = time.time()

    # -- roster / connections ----------------------------------------------
    async def connect(self, name: str, connection: Connection) -> str:
        player_id = uuid.uuid4().hex[:8]
        player = Player(id=player_id, name=name)
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
                await self._handle_submit(player_id, message.prompt)
            case p.PlayAgain():
                await self._handle_play_again(player_id)

    async def _handle_start(self, player_id: str) -> None:
        if self.state.host_id() != player_id:
            await self._send(player_id, p.ErrorMessage(detail="Only the host can start the game."))
            return
        if self.state.phase != Phase.LOBBY:
            await self._send(player_id, p.ErrorMessage(detail="Game already in progress."))
            return
        self._game_task = asyncio.create_task(self._run_game())

    async def _handle_submit(self, player_id: str, prompt: str) -> None:
        rnd = self.state.current_round
        if self.state.phase != Phase.PROMPTING or rnd is None:
            await self._send(player_id, p.ErrorMessage(detail="Not accepting prompts right now."))
            return
        rnd.submissions[player_id] = Submission(player_id=player_id, prompt=prompt)
        await self._send(player_id, p.PromptAccepted())
        await self._broadcast(
            p.SubmissionCount(
                submitted=len(rnd.submissions),
                total=len(self.state.connected_players()),
            )
        )
        self._submission_event.set()

    async def _handle_play_again(self, player_id: str) -> None:
        if self.state.host_id() != player_id:
            return
        if self.state.phase != Phase.GAME_OVER:
            return
        for pl in self.state.players.values():
            pl.score = 0
        self.state.phase = Phase.LOBBY
        self.state.round_num = 0
        self.state.current_round = None
        self.state.deadline_ts = None
        self._images.clear()
        await self._broadcast(self._room_state())

    # -- the game loop ------------------------------------------------------
    async def _run_game(self) -> None:
        for round_num in range(1, self.state.total_rounds + 1):
            self.state.round_num = round_num
            if not self.state.connected_players():
                break
            await self._generate_target(round_num)
            await self._prompting_phase()
            await self._generate_results()
            await self._judging_phase()
            await self._reveal_phase(round_num)

        self.state.phase = Phase.GAME_OVER
        await self._broadcast(self._phase_changed())
        winner = standings(self.state)
        await self._broadcast(
            p.GameOver(
                standings=self._player_views(),
                winner_id=winner[0].id if winner else None,
            )
        )

    async def _generate_target(self, round_num: int) -> None:
        self.state.phase = Phase.GENERATING_TARGET
        await self._broadcast(self._phase_changed())
        seed_prompt = random_seed_prompt()
        image = await self._generator.generate(seed_prompt)
        target_id = self._store_image(image)
        self.state.current_round = RoundResult(target_image_id=target_id)
        await self._broadcast(p.TargetReady(image_id=target_id, round_num=round_num))

    async def _prompting_phase(self) -> None:
        self.state.phase = Phase.PROMPTING
        self._submission_event.clear()
        loop = asyncio.get_event_loop()
        mono_deadline = loop.time() + self.state.round_seconds
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

    async def _generate_results(self) -> None:
        self.state.phase = Phase.GENERATING_RESULTS
        await self._broadcast(self._phase_changed())
        rnd = self.state.current_round
        assert rnd is not None
        prompts = {pid: sub.prompt for pid, sub in rnd.submissions.items()}
        images = await generate_many(self._generator, prompts, concurrency=self._concurrency)
        for pid, image in images.items():
            image_id = self._store_image(image)
            rnd.submissions[pid].image_id = image_id

    async def _judging_phase(self) -> None:
        self.state.phase = Phase.JUDGING
        await self._broadcast(self._phase_changed())
        rnd = self.state.current_round
        assert rnd is not None

        judge_inputs: list[JudgeInput] = []
        for pid, sub in rnd.submissions.items():
            if sub.image_id is None:
                continue
            player = self.state.players.get(pid)
            image = self._images[sub.image_id]
            judge_inputs.append(
                JudgeInput(
                    player_id=pid,
                    player_name=player.name if player else pid,
                    prompt=sub.prompt,
                    image_bytes=image.image_bytes,
                    content_type=image.content_type,
                )
            )

        target = self._images[rnd.target_image_id]
        verdicts = await self._judge.judge(
            target.image_bytes, judge_inputs, target_content_type=target.content_type
        )

        # Every player gets a score this round; non-submitters score 0.
        scores: dict[str, int] = {pid: 0 for pid in self.state.players}
        for pid, verdict in verdicts.items():
            scores[pid] = verdict.score
            rnd.rationales[pid] = verdict.rationale
        self.state.apply_scores(scores)

    async def _reveal_phase(self, round_num: int) -> None:
        self.state.phase = Phase.REVEAL
        rnd = self.state.current_round
        assert rnd is not None
        results: list[p.ResultView] = []
        for pid, sub in rnd.submissions.items():
            player = self.state.players.get(pid)
            results.append(
                p.ResultView(
                    player_id=pid,
                    player_name=player.name if player else pid,
                    prompt=sub.prompt,
                    image_id=sub.image_id,
                    score=rnd.scores.get(pid),
                    rationale=rnd.rationales.get(pid),
                )
            )
        results.sort(key=lambda r: -(r.score or 0))
        await self._broadcast(self._phase_changed())
        await self._broadcast(
            p.RoundReveal(
                round_num=round_num,
                target_image_id=rnd.target_image_id,
                results=results,
                winner_id=round_winner(rnd),
                standings=self._player_views(),
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
