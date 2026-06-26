"""Seed prompts used to generate a fresh target image each round.

Kept deliberately concrete and varied (subject + setting + mood) so targets are
interesting to reverse-engineer with a prompt.
"""

from __future__ import annotations

import random

SEED_PROMPTS: list[str] = [
    "a lighthouse on a rocky cliff at sunset, dramatic orange sky",
    "a cozy bookstore cafe interior, warm lamplight, rainy window",
    "a red fox curled asleep in a snowy forest clearing",
    "a futuristic city skyline at night with neon reflections in water",
    "a hot air balloon drifting over green rolling hills at dawn",
    "a still life of lemons and a ceramic jug on a wooden table",
    "an astronaut planting a flag on a purple alien desert",
    "a koi pond in a Japanese garden with a small wooden bridge",
    "a vintage diner on a desert highway under a starry sky",
    "a giant whale swimming above a sunken city, shafts of light",
    "a market stall overflowing with colorful spices and fruit",
    "a lone cabin in a pine forest with smoke rising from the chimney",
    "a steaming bowl of ramen with chopsticks, dark moody lighting",
    "a hummingbird hovering at a bright pink flower, macro shot",
    "a medieval castle on a misty mountain at golden hour",
    "a surfer riding a huge turquoise wave, spray in the air",
]


def random_seed_prompt(rng: random.Random | None = None) -> str:
    rng = rng or random
    return rng.choice(SEED_PROMPTS)
