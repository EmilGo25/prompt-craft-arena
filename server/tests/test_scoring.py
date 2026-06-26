import pytest

from server.services.judge import RandomJudge, JudgeInput
from server.services.scoring import ScoreWeights, compose_score, speed_bonus


def test_speed_bonus_bounds():
    assert speed_bonus(0.0) == 100   # instant submit -> full bonus
    assert speed_bonus(1.0) == 0     # at the buzzer -> none
    assert speed_bonus(0.5) == 50
    assert speed_bonus(-0.2) == 100  # clamped
    assert speed_bonus(2.0) == 0     # clamped


def test_compose_weights_sum_to_one_keeps_scale():
    # similarity 100, slowest submit -> final = 100*0.8 + 0*0.2 = 80
    b = compose_score(100, 1.0, "r", {"subject": 100})
    assert b.final == 80
    assert b.similarity == 100
    assert b.speed_bonus == 0

    # similarity 50, instant submit -> 50*0.8 + 100*0.2 = 60
    b2 = compose_score(50, 0.0, "r", {})
    assert b2.final == 60


def test_similarity_dominates_speed():
    slow_great = compose_score(90, 1.0, "", {})   # 72
    fast_poor = compose_score(20, 0.0, "", {})    # 36
    assert slow_great.final > fast_poor.final


def test_custom_weights():
    b = compose_score(0, 0.0, "", {}, weights=ScoreWeights(similarity=0.5, speed=0.5))
    assert b.final == 50  # 0*0.5 + 100*0.5


@pytest.mark.asyncio
async def test_random_judge_returns_dimensions():
    v = await RandomJudge().judge_one(
        b"target", JudgeInput("p", "Ann", "cat", b"img")
    )
    assert 0 <= v.score <= 100
    assert set(v.dimensions) == {"subject", "composition", "color", "mood"}
