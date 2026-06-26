"""Scoring: how close is each generated image to the target?

``ClaudeJudge`` sends the target plus every result image to a multimodal Claude
model in one request and gets back a validated array of per-player scores via
structured output. ``RandomJudge`` returns arbitrary scores so the game runs
offline with no API key.
"""

from __future__ import annotations

import base64
import random
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Verdict:
    score: int  # 0-100
    rationale: str


@dataclass(frozen=True)
class JudgeInput:
    player_id: str
    player_name: str
    prompt: str
    image_bytes: bytes
    content_type: str = "image/png"


class Judge(Protocol):
    async def judge(
        self, target_bytes: bytes, results: list[JudgeInput], *, target_content_type: str = "image/png"
    ) -> dict[str, Verdict]:
        ...


# ---------------------------------------------------------------------------
# Random stub
# ---------------------------------------------------------------------------


class RandomJudge:
    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()

    async def judge(
        self, target_bytes: bytes, results: list[JudgeInput], *, target_content_type: str = "image/png"
    ) -> dict[str, Verdict]:
        return {
            r.player_id: Verdict(
                score=self._rng.randint(0, 100),
                rationale="(random judge)",
            )
            for r in results
        }


# ---------------------------------------------------------------------------
# Claude judge
# ---------------------------------------------------------------------------

RUBRIC = (
    "You are the judge in a prompt-writing game. Players were shown a TARGET "
    "image and each wrote a prompt; an image model produced a RESULT image from "
    "each prompt. Score how closely each RESULT matches the TARGET on subject, "
    "composition, color palette, and overall mood. Give an integer 0-100 (100 = "
    "near-identical) and a one-sentence rationale for each player. Judge only "
    "visual similarity to the target; ignore artistic quality on its own."
)

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "player_id": {"type": "string"},
                    "score": {"type": "integer"},
                    "rationale": {"type": "string"},
                },
                "required": ["player_id", "score", "rationale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["scores"],
    "additionalProperties": False,
}


def _image_block(image_bytes: bytes, content_type: str) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": content_type,
            "data": base64.standard_b64encode(image_bytes).decode(),
        },
    }


class ClaudeJudge:
    def __init__(self, api_key: str, *, model: str = "claude-opus-4-8") -> None:
        if not api_key:
            raise ValueError("ClaudeJudge requires an Anthropic API key")
        # Imported lazily so the stub path needs no anthropic install at runtime.
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def judge(
        self, target_bytes: bytes, results: list[JudgeInput], *, target_content_type: str = "image/png"
    ) -> dict[str, Verdict]:
        if not results:
            return {}

        content: list[dict] = [
            {"type": "text", "text": RUBRIC},
            {"type": "text", "text": "TARGET image:"},
            _image_block(target_bytes, target_content_type),
        ]
        for r in results:
            content.append(
                {
                    "type": "text",
                    "text": f'RESULT from player_id="{r.player_id}" '
                    f'(prompt: "{r.prompt}"):',
                }
            )
            content.append(_image_block(r.image_bytes, r.content_type))

        try:
            resp = await self._client.messages.create(
                model=self._model,
                max_tokens=2000,
                output_config={"format": {"type": "json_schema", "schema": SCORE_SCHEMA}},
                messages=[{"role": "user", "content": content}],
            )
            payload = _extract_json(resp)
        except Exception:  # noqa: BLE001 - degrade to a neutral tie, never crash a round
            return {r.player_id: Verdict(50, "(judge unavailable)") for r in results}

        verdicts: dict[str, Verdict] = {}
        for item in payload.get("scores", []):
            pid = item.get("player_id")
            if pid is not None:
                verdicts[pid] = Verdict(
                    score=max(0, min(100, int(item.get("score", 0)))),
                    rationale=str(item.get("rationale", "")),
                )
        # Any player Claude skipped gets a neutral score so reveal is complete.
        for r in results:
            verdicts.setdefault(r.player_id, Verdict(0, "(no verdict returned)"))
        return verdicts


def _extract_json(resp) -> dict:
    import json

    for block in resp.content:
        if getattr(block, "type", None) == "text":
            return json.loads(block.text)
    return {}


def build_judge(judge_kind: str, *, anthropic_api_key: str = "", model: str = "claude-opus-4-8") -> Judge:
    if judge_kind == "claude":
        return ClaudeJudge(anthropic_api_key, model=model)
    if judge_kind == "random":
        return RandomJudge()
    raise ValueError(f"Unknown judge: {judge_kind!r}")
