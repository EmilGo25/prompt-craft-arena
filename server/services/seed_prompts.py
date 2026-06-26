"""Target-image prompts, engineered for reverse-prompting difficulty.

The game is about *reverse-engineering* a target image: players see the image and
write a prompt to recreate it. Difficulty is tuned on two research-backed levers
(see PRINCIPLES.md / decisions.md):

1. **Concept→words translation** — how many distinct, describable cues the image
   has. More cues = harder to capture them all.
2. **Design ontology** — whether naming the look requires vocabulary like
   "chiaroscuro", "isometric", "Dutch angle".

The fairness rule: every cue must be **observable and nameable**. We deliberately
avoid "unfair-hard" features — text in the image, exact counts beyond a few,
named artists/IP, micro-detail — so skill is careful observation + precise
wording, never guessing the unknowable.

Each target is assembled to carry a clear value on every axis the judge scores
(subject, composition, color, mood) plus a style/medium, so a thoughtful player
can score well and a lazy one-word prompt cannot.
"""

from __future__ import annotations

import random
from enum import StrEnum


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


# A single, paintable subject (the most heavily weighted axis: must be distinctive
# but nameable).
SUBJECTS = [
    "a lone red fox", "a brass diving helmet", "a paper sailboat", "a hot-air balloon",
    "a grand piano", "a snowy owl", "a vintage motorcycle", "a koi fish", "a lighthouse",
    "a stone cottage", "an astronaut", "a stag with tall antlers", "an old typewriter",
    "a glowing jellyfish", "a potted cactus", "a polar bear", "a steam locomotive",
    "a violin", "a treehouse", "a humpback whale", "a hummingbird", "a carousel horse",
    "a teapot", "a wooden rowboat",
]

# A second subject for hard juxtapositions (surreal but still describable).
SECOND_SUBJECTS = [
    "a giant floating clock", "a flock of paper cranes", "a curious deer", "a small robot",
    "a swarm of fireflies", "an enormous low moon", "a drifting hot-air balloon",
    "a school of glowing fish",
]

SETTINGS = [
    "a misty pine forest", "a neon-lit city street", "a quiet desert at dusk",
    "an underwater coral reef", "a snowy mountain pass", "a sunlit meadow",
    "a rainy train platform", "a cozy cluttered attic", "a windswept sea cliff",
    "a foggy harbor", "a vast white salt flat", "a flooded ancient temple",
    "a rooftop garden at night", "a frozen lake",
]

# Medium / art style — the "ontology" axis. No named artists or studios (fair + no IP).
STYLES = [
    "watercolor painting", "cinematic photograph", "oil painting", "low-poly 3D render",
    "detailed pencil sketch", "vaporwave digital art", "soft anime style",
    "flat vector illustration", "long-exposure photograph", "impressionist painting",
    "isometric 3D illustration", "charcoal drawing", "stained-glass art",
]

# Camera / framing — ontology that separates careful observers from guessers.
COMPOSITIONS = [
    "extreme close-up", "wide establishing shot", "low-angle view", "bird's-eye view",
    "symmetrical centered composition", "shallow depth of field", "Dutch angle",
    "silhouette against the sky",
]

LIGHTING = [
    "golden-hour backlight", "soft diffused light", "dramatic chiaroscuro lighting",
    "glowing neon light", "moonlit", "warm candlelight", "cool blue twilight",
    "volumetric god rays",
]

# Color palette (the "color" axis).
PALETTES = [
    "muted earth tones", "vivid teal-and-orange", "monochrome blue", "pastel pink and mint",
    "warm autumn", "high-contrast black and white", "deep jewel tones", "faded sepia",
]

MOODS = [
    "serene and dreamy", "lonely and nostalgic", "epic and awe-inspiring",
    "playful and whimsical", "eerie and mysterious", "cozy and warm", "tense and dramatic",
]

# Optional surreal twist for hard rounds — memorable but still nameable.
TWISTS = [
    "made of glass", "impossibly oversized", "wrapped in glowing threads",
    "sprouting flowers", "floating in midair",
]


class TargetPromptGenerator:
    """Assembles a target prompt at a given difficulty from the component banks.

    Pass a seeded ``random.Random`` for deterministic tests.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    def generate(self, difficulty: Difficulty | str = Difficulty.MEDIUM) -> str:
        diff = Difficulty(difficulty)
        pick = self._rng.choice
        subject = pick(SUBJECTS)

        if diff is Difficulty.EASY:
            # 3 cues: subject, setting, style. Approachable, still not one word.
            return f"{subject} in {pick(SETTINGS)}, {pick(STYLES)}"

        if diff is Difficulty.MEDIUM:
            # ~5 cues spanning all four judged axes + style. Challenging but fair.
            return (
                f"{subject} in {pick(SETTINGS)}, "
                f"{pick(LIGHTING)}, {pick(PALETTES)} palette, "
                f"{pick(STYLES)}, {pick(MOODS)} mood"
            )

        # HARD: a juxtaposition + explicit camera framing + the full axis set, and
        # sometimes a surreal twist. Every cue is still observable.
        subj = f"{subject} {pick(TWISTS)}" if self._rng.random() < 0.4 else subject
        return (
            f"{subj} and {pick(SECOND_SUBJECTS)} in {pick(SETTINGS)}, "
            f"{pick(COMPOSITIONS)}, {pick(LIGHTING)}, {pick(PALETTES)} palette, "
            f"{pick(STYLES)}, {pick(MOODS)} mood"
        )


def difficulty_for_round(round_num: int, total_rounds: int) -> Difficulty:
    """Ramp difficulty across a game: ease players in, finish hard."""
    if total_rounds <= 1:
        return Difficulty.MEDIUM
    frac = (round_num - 1) / (total_rounds - 1)
    if frac < 0.34:
        return Difficulty.EASY
    if frac < 0.67:
        return Difficulty.MEDIUM
    return Difficulty.HARD


# Back-compat helper (used by older call sites / tests): a medium target.
def random_seed_prompt(rng: random.Random | None = None) -> str:
    return TargetPromptGenerator(rng).generate(Difficulty.MEDIUM)
