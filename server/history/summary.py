"""Plain, DB-free data the Room hands to a recorder at game over.

Keeping these as pure dataclasses (with raw image bytes) lets the Room build a
complete snapshot without importing anything DB-related, and lets the recorder
(history/recorder.py) own all persistence concerns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ResultSnapshot:
    player_id: str
    user_id: str | None
    display_name: str
    prompt: str
    score: int
    rationale: str
    image_bytes: bytes | None
    content_type: str = "image/png"


@dataclass
class RoundSnapshot:
    round_num: int
    target_image_bytes: bytes
    target_content_type: str
    results: list[ResultSnapshot] = field(default_factory=list)


@dataclass
class ParticipantSnapshot:
    player_id: str
    user_id: str | None
    display_name: str
    final_score: int
    placement: int  # 1 = winner


@dataclass
class GameSummary:
    code: str
    total_rounds: int
    round_seconds: int
    winner_name: str | None
    participants: list[ParticipantSnapshot] = field(default_factory=list)
    rounds: list[RoundSnapshot] = field(default_factory=list)

    def has_authenticated_participant(self) -> bool:
        return any(p.user_id is not None for p in self.participants)


class GameRecorder(Protocol):
    async def record(self, summary: GameSummary) -> None:
        ...
