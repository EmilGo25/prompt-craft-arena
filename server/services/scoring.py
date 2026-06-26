"""Composite round score = LLM-judge similarity + submission-speed bonus.

The judge supplies the holistic visual-similarity score (0-100). On top of that
we reward submitting early: a player who locks in their prompt quickly gets a
speed bonus. The two are combined with weights that sum to 1, so the final score
stays on a 0-100 scale and similarity always dominates.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ScoreWeights:
    similarity: float = 0.8  # how much the image-match matters
    speed: float = 0.2  # how much submitting early matters


@dataclass(frozen=True)
class ScoreBreakdown:
    final: int  # the round score that counts (0-100)
    similarity: int  # judge's holistic similarity (0-100)
    speed_bonus: int  # 0-100, 100 = submitted instantly
    rationale: str  # judge's written summary
    dimensions: dict[str, int] = field(default_factory=dict)  # subject/composition/color/mood


def speed_bonus(submit_fraction: float) -> int:
    """Map fraction-of-time-used (0=instant, 1=at the buzzer) to a 0-100 bonus."""
    frac = max(0.0, min(1.0, submit_fraction))
    return round((1.0 - frac) * 100)


def compose_score(
    similarity: int,
    submit_fraction: float,
    rationale: str,
    dimensions: dict[str, int],
    *,
    weights: ScoreWeights = ScoreWeights(),
) -> ScoreBreakdown:
    bonus = speed_bonus(submit_fraction)
    final = round(similarity * weights.similarity + bonus * weights.speed)
    return ScoreBreakdown(
        final=max(0, min(100, final)),
        similarity=similarity,
        speed_bonus=bonus,
        rationale=rationale,
        dimensions=dimensions,
    )
