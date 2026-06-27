"""The wire protocol: every client<->server message as a typed Pydantic model.

Messages are discriminated on a ``type`` literal. Both directions parse the
opposite side's union so an unknown/invalid message is rejected, not guessed.

Images never travel inline here — they are referenced by ``image_id`` and
fetched over HTTP from ``GET /rooms/{code}/images/{image_id}`` so WS frames stay
small.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

# ---------------------------------------------------------------------------
# Client -> Server
# ---------------------------------------------------------------------------


class StartGame(BaseModel):
    type: Literal["start_game"] = "start_game"


class SubmitPrompt(BaseModel):
    type: Literal["submit_prompt"] = "submit_prompt"
    prompt: str = Field(min_length=1, max_length=1000)
    lang: str = "en"  # language for the judge's written rationale


class PlayAgain(BaseModel):
    type: Literal["play_again"] = "play_again"


class Ping(BaseModel):
    type: Literal["ping"] = "ping"


ClientMessage = Annotated[
    Union[StartGame, SubmitPrompt, PlayAgain, Ping],
    Field(discriminator="type"),
]


_client_adapter: TypeAdapter[ClientMessage] = TypeAdapter(ClientMessage)


def parse_client_message(raw: str | bytes) -> ClientMessage:
    """Parse raw inbound JSON into a validated ClientMessage (raises on garbage)."""
    return _client_adapter.validate_json(raw)


# ---------------------------------------------------------------------------
# Server -> Client (shared sub-models)
# ---------------------------------------------------------------------------


class PlayerView(BaseModel):
    id: str
    name: str
    score: int
    connected: bool
    is_host: bool
    picture_url: str | None = None


class ResultView(BaseModel):
    player_id: str
    player_name: str
    prompt: str
    image_id: str | None
    score: int | None = None  # final composite score (counts toward standings)
    similarity: int | None = None  # LLM-judge holistic visual match
    speed_bonus: int | None = None  # submission-speed component
    rationale: str | None = None  # judge's written summary
    dimensions: dict[str, int] | None = None  # subject/composition/color/mood subscores


# ---------------------------------------------------------------------------
# Server -> Client (messages)
# ---------------------------------------------------------------------------


class Welcome(BaseModel):
    """First message after a successful join: tells the client who it is."""

    type: Literal["welcome"] = "welcome"
    player_id: str
    room_code: str


class RoomState(BaseModel):
    """Full snapshot — sent on join and whenever the lobby roster changes."""

    type: Literal["room_state"] = "room_state"
    phase: str
    round_num: int
    total_rounds: int
    players: list[PlayerView]


class PhaseChanged(BaseModel):
    type: Literal["phase_changed"] = "phase_changed"
    phase: str
    round_num: int


class TargetReady(BaseModel):
    type: Literal["target_ready"] = "target_ready"
    image_id: str
    round_num: int


class Timer(BaseModel):
    type: Literal["timer"] = "timer"
    seconds_left: int
    deadline_ts: float


class PromptAccepted(BaseModel):
    """Echoed to a player when their submission is recorded."""

    type: Literal["prompt_accepted"] = "prompt_accepted"


class SubmissionStatus(BaseModel):
    """Broadcast as submissions arrive: which players have submitted, for the
    per-player placeholder tiles during PROMPTING."""

    type: Literal["submission_status"] = "submission_status"
    submitted_player_ids: list[str]
    total: int


class RoundReveal(BaseModel):
    type: Literal["round_reveal"] = "round_reveal"
    round_num: int
    target_image_id: str
    results: list[ResultView]
    winner_id: str | None
    standings: list[PlayerView]


class GameOver(BaseModel):
    type: Literal["game_over"] = "game_over"
    standings: list[PlayerView]
    winner_id: str | None


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    detail: str


class Pong(BaseModel):
    type: Literal["pong"] = "pong"


ServerMessage = Union[
    Welcome,
    RoomState,
    PhaseChanged,
    TargetReady,
    Timer,
    PromptAccepted,
    SubmissionStatus,
    RoundReveal,
    GameOver,
    ErrorMessage,
    Pong,
]
