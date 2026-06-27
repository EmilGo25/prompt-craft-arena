"""Scoring: how close is a generated image to the target?

Each player's image is judged independently the moment it is generated, so they
get a similarity score plus a written summary right away. The judge returns a
holistic 0-100 ``score`` plus per-dimension subscores (subject / composition /
color / mood) so the game can show *why* a score was given. The submission-speed
bonus is applied separately in ``scoring.py`` — the judge only assesses the
image.

``OpenAIJudge`` uses a carefully structured system prompt (role, weighted
dimensions, calibration anchors, guardrails) and structured outputs so scores are
consistent and parseable. ``RandomJudge`` returns arbitrary verdicts so the game
runs offline with no API key.
"""

from __future__ import annotations

import base64
import random
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Verdict:
    score: int  # holistic similarity 0-100
    rationale: str
    dimensions: dict[str, int] = field(default_factory=dict)  # subject/composition/color/mood


@dataclass(frozen=True)
class JudgeInput:
    player_id: str
    player_name: str
    prompt: str
    image_bytes: bytes
    content_type: str = "image/png"


# Language code -> name for the rationale instruction. Unknown codes fall back to English.
LANGUAGE_NAMES = {"en": "English", "he": "Hebrew"}


class Judge(Protocol):
    async def judge_one(
        self,
        target_bytes: bytes,
        result: JudgeInput,
        *,
        target_content_type: str = "image/png",
        language: str = "en",
    ) -> Verdict:
        ...


# ---------------------------------------------------------------------------
# Random stub
# ---------------------------------------------------------------------------

_DIMENSIONS = ("subject", "composition", "color", "mood")


class RandomJudge:
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    async def judge_one(
        self,
        target_bytes: bytes,
        result: JudgeInput,
        *,
        target_content_type: str = "image/png",
        language: str = "en",
    ) -> Verdict:
        dims = {d: self._rng.randint(0, 100) for d in _DIMENSIONS}
        return Verdict(
            score=round(sum(dims.values()) / len(dims)),
            rationale="(random judge)",
            dimensions=dims,
        )


# ---------------------------------------------------------------------------
# Claude judge
# ---------------------------------------------------------------------------

# System prompt structure (LLM-as-judge best practice):
#   1. Role  2. Task  3. Weighted dimensions  4. Calibration anchors
#   5. Guardrails  6. Output contract
JUDGE_SYSTEM = """\
You are an expert visual-similarity judge for a competitive prompt-writing game. \
Players are shown a TARGET image and write a prompt; an image model turns each \
prompt into a RESULT image. Your job is to score how faithfully a RESULT \
recreates the TARGET.

Score these four dimensions, each 0-100, in rough order of importance:
- subject: Are the same main subjects/objects present and dominant? (most important)
- composition: Do layout, framing, perspective, and the arrangement of elements match?
- color: Do the color palette, tone, and lighting match?
- mood: Do the overall atmosphere, genre, and artistic style match?

Then give a holistic overall score 0-100 using these calibration anchors:
- 90-100: Near-identical. A viewer could mistake one image for the other.
- 70-89: Clearly the same scene/subject; only minor differences in detail or color.
- 50-69: Related; the main subject is recognizable but with notable differences.
- 30-49: Some shared elements, but wrong subject, composition, or mood.
- 10-29: Only loosely related.
- 0-9: Unrelated.

Guardrails:
- Judge ONLY similarity to the TARGET, never standalone artistic quality or polish.
- Weight the main subject most; heavily penalize a missing or wrong main subject, \
and penalize major extra elements that aren't in the target.
- Be objective and consistent across players; identical resemblance must get the \
same score regardless of order.
- Ignore minor, unavoidable image-generation artifacts.
- Judge the IMAGES only. Do not reward clever wording in the prompt.

Return your verdict via the provided structured format. The rationale must be one \
or two sentences naming the single biggest match and the single biggest difference.\
"""

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "integer"},
        "composition": {"type": "integer"},
        "color": {"type": "integer"},
        "mood": {"type": "integer"},
        "overall": {"type": "integer"},
        "rationale": {"type": "string"},
    },
    "required": ["subject", "composition", "color", "mood", "overall", "rationale"],
    "additionalProperties": False,
}


def _data_url(image_bytes: bytes, content_type: str) -> str:
    return f"data:{content_type};base64,{base64.standard_b64encode(image_bytes).decode()}"


def _clamp(v: object) -> int:
    try:
        return max(0, min(100, int(v)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


class OpenAIJudge:
    def __init__(self, api_key: str, *, model: str = "gpt-4o") -> None:
        if not api_key:
            raise ValueError("OpenAIJudge requires an OpenAI API key")
        from openai import AsyncOpenAI  # lazy: stub path needs no SDK at runtime

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def judge_one(
        self,
        target_bytes: bytes,
        result: JudgeInput,
        *,
        target_content_type: str = "image/png",
        language: str = "en",
    ) -> Verdict:
        language_name = LANGUAGE_NAMES.get(language, "English")
        user_content = [
            {"type": "text", "text": "TARGET image:"},
            {"type": "image_url", "image_url": {"url": _data_url(target_bytes, target_content_type)}},
            {"type": "text", "text": "RESULT image to score against the target:"},
            {"type": "image_url", "image_url": {"url": _data_url(result.image_bytes, result.content_type)}},
            {
                "type": "text",
                "text": f"Write the `rationale` field in {language_name}. "
                "The numeric scores are unaffected by language.",
            },
        ]
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "verdict", "strict": True, "schema": VERDICT_SCHEMA},
                },
            )
            import json

            data = json.loads(resp.choices[0].message.content)
        except Exception:  # noqa: BLE001 - degrade to neutral, never crash a round
            return Verdict(50, "(judge unavailable)", {d: 50 for d in _DIMENSIONS})

        dims = {d: _clamp(data.get(d)) for d in _DIMENSIONS}
        return Verdict(
            score=_clamp(data.get("overall")),
            rationale=str(data.get("rationale", "")),
            dimensions=dims,
        )


def build_judge(judge_kind: str, *, openai_api_key: str = "", model: str = "gpt-4o") -> Judge:
    if judge_kind == "openai":
        return OpenAIJudge(openai_api_key, model=model)
    if judge_kind == "random":
        return RandomJudge()
    raise ValueError(f"Unknown judge: {judge_kind!r}")
