import random

from server.services.seed_prompts import (
    Difficulty,
    TargetPromptGenerator,
    difficulty_for_round,
)


def test_difficulty_adds_cues():
    # Harder targets carry more describable cues (longer, more comma-separated parts).
    gen = TargetPromptGenerator(random.Random(0))
    easy = gen.generate(Difficulty.EASY)
    medium = gen.generate(Difficulty.MEDIUM)
    hard = gen.generate(Difficulty.HARD)
    assert easy.count(",") < medium.count(",") < hard.count(",")


def test_deterministic_with_seed():
    a = TargetPromptGenerator(random.Random(42)).generate("medium")
    b = TargetPromptGenerator(random.Random(42)).generate("medium")
    assert a == b


def test_accepts_string_or_enum():
    gen = TargetPromptGenerator(random.Random(1))
    assert isinstance(gen.generate("hard"), str)
    assert isinstance(gen.generate(Difficulty.EASY), str)


def test_hard_has_two_subjects():
    # Hard targets juxtapose two subjects ("... and ...").
    gen = TargetPromptGenerator(random.Random(3))
    assert " and " in gen.generate(Difficulty.HARD)


def test_ramp_eases_in_and_finishes_hard():
    assert difficulty_for_round(1, 5) is Difficulty.EASY
    assert difficulty_for_round(3, 5) is Difficulty.MEDIUM
    assert difficulty_for_round(5, 5) is Difficulty.HARD
    # Single-round game is medium, not trivially easy.
    assert difficulty_for_round(1, 1) is Difficulty.MEDIUM
