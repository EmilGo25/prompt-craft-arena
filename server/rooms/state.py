"""Core game state: the round state machine, data model, and pure scoring logic.

Everything here is plain data + pure functions so it can be unit-tested without
any I/O (no network, no event loop). The Room (room.py) drives transitions and
owns the side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..services.scoring import ScoreBreakdown


class Phase(StrEnum):
    LOBBY = "lobby"
    GENERATING_TARGET = "generating_target"
    PROMPTING = "prompting"
    SCORING = "scoring"  # "waiting for score": images generated + judged for all submissions
    REVEAL = "reveal"
    GAME_OVER = "game_over"


@dataclass
class Player:
    id: str
    name: str
    score: int = 0
    connected: bool = True
    is_host: bool = False
    user_id: str | None = None  # set when the player is an authenticated user
    picture_url: str | None = None


@dataclass
class Submission:
    player_id: str
    prompt: str
    submit_fraction: float = 0.0  # 0 = instant, 1 = at the buzzer (drives speed bonus)
    image_id: str | None = None  # set once the result image is generated
    breakdown: ScoreBreakdown | None = None  # set once generated + judged + composed


@dataclass
class RoundResult:
    target_image_id: str
    submissions: dict[str, Submission] = field(default_factory=dict)
    scores: dict[str, int] = field(default_factory=dict)  # final score per player, cumulative


@dataclass
class GameState:
    total_rounds: int
    round_seconds: int
    phase: Phase = Phase.LOBBY
    round_num: int = 0  # 1-based once the game starts; 0 in lobby
    players: dict[str, Player] = field(default_factory=dict)
    current_round: RoundResult | None = None
    deadline_ts: float | None = None  # epoch seconds when PROMPTING ends

    # --- player management -------------------------------------------------
    def add_player(self, player: Player) -> None:
        if not self.players:
            player.is_host = True
        self.players[player.id] = player

    def host_id(self) -> str | None:
        for p in self.players.values():
            if p.is_host:
                return p.id
        return None

    def connected_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.connected]

    # --- round resolution --------------------------------------------------
    def all_connected_submitted(self) -> bool:
        """True if every connected player has submitted a prompt this round."""
        rnd = self.current_round
        if rnd is None:
            return False
        connected = self.connected_players()
        if not connected:
            return False
        return all(p.id in rnd.submissions for p in connected)

    def apply_scores(self, scores: dict[str, int]) -> None:
        """Record this round's scores and add them to cumulative totals."""
        assert self.current_round is not None
        self.current_round.scores = scores
        for player_id, points in scores.items():
            if player_id in self.players:
                self.players[player_id].score += points


def standings(state: GameState) -> list[Player]:
    """Players ranked by cumulative score (desc), stable by join order."""
    return sorted(state.players.values(), key=lambda p: -p.score)


def round_winner(result: RoundResult) -> str | None:
    """player_id with the highest score this round, or None if no scores."""
    if not result.scores:
        return None
    return max(result.scores, key=lambda pid: result.scores[pid])
