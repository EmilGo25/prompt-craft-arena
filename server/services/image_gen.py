"""Image generation behind a pluggable interface.

This is the one place that talks to an external image model. The
``StubImageGenerator`` renders the prompt text onto a deterministic colored card
with Pillow, so the entire game runs offline with no API keys.
``OpenAIImageGenerator`` calls OpenAI's image API (gpt-image-1).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import textwrap
from dataclasses import dataclass
from typing import Protocol

from PIL import Image, ImageDraw


@dataclass(frozen=True)
class GeneratedImage:
    image_bytes: bytes
    content_type: str = "image/png"


class ImageGenerator(Protocol):
    async def generate(self, prompt: str, *, seed: int | None = None) -> GeneratedImage:
        ...


# ---------------------------------------------------------------------------
# Stub — deterministic, offline, no keys
# ---------------------------------------------------------------------------


def _color_from(text: str) -> tuple[int, int, int]:
    h = hashlib.sha256(text.encode()).digest()
    return h[0], h[1], h[2]


def _contrast_text_color(bg: tuple[int, int, int]) -> tuple[int, int, int]:
    luminance = 0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]
    return (0, 0, 0) if luminance > 140 else (255, 255, 255)


class StubImageGenerator:
    """Renders the prompt as text on a color derived from it. Deterministic."""

    def __init__(self, size: int = 512) -> None:
        self.size = size

    async def generate(self, prompt: str, *, seed: int | None = None) -> GeneratedImage:
        key = f"{prompt}|{seed}" if seed is not None else prompt
        bg = _color_from(key)
        img = Image.new("RGB", (self.size, self.size), bg)
        draw = ImageDraw.Draw(img)
        fg = _contrast_text_color(bg)
        wrapped = textwrap.fill(prompt, width=24)[:400]
        draw.multiline_text(
            (self.size // 2, self.size // 2),
            wrapped,
            fill=fg,
            anchor="mm",
            align="center",
            spacing=6,
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return GeneratedImage(image_bytes=buf.getvalue())


# ---------------------------------------------------------------------------
# OpenAI image API (gpt-image-1)
# ---------------------------------------------------------------------------


class OpenAIImageGenerator:
    """Calls OpenAI's image API. Needs OPENAI_API_KEY. Returns PNG bytes."""

    def __init__(
        self, api_key: str, *, model: str = "gpt-image-1", size: str = "1024x1024"
    ) -> None:
        if not api_key:
            raise ValueError("OpenAIImageGenerator requires an OpenAI API key")
        from openai import AsyncOpenAI  # lazy: stub path needs no SDK at runtime

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._size = size

    async def generate(self, prompt: str, *, seed: int | None = None) -> GeneratedImage:
        resp = await self._client.images.generate(
            model=self._model,
            prompt=prompt,
            size=self._size,
            n=1,
        )
        b64 = resp.data[0].b64_json
        return GeneratedImage(image_bytes=base64.b64decode(b64), content_type="image/png")


def build_image_generator(
    provider: str,
    *,
    openai_api_key: str = "",
    openai_image_model: str = "gpt-image-1",
    openai_image_size: str = "1024x1024",
) -> ImageGenerator:
    if provider == "openai":
        return OpenAIImageGenerator(
            openai_api_key, model=openai_image_model, size=openai_image_size
        )
    if provider == "stub":
        return StubImageGenerator()
    raise ValueError(f"Unknown image provider: {provider!r}")


async def generate_many(
    generator: ImageGenerator,
    prompts: dict[str, str],
    *,
    concurrency: int = 4,
) -> dict[str, GeneratedImage]:
    """Generate one image per (key -> prompt), bounded by a semaphore.

    A failure for one key is swallowed (that key is omitted) so one bad prompt
    can't sink the whole round.
    """
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, GeneratedImage] = {}

    async def _one(key: str, prompt: str) -> None:
        async with sem:
            try:
                results[key] = await generator.generate(prompt)
            except Exception:  # noqa: BLE001 - isolate per-prompt failures
                pass

    await asyncio.gather(*(_one(k, p) for k, p in prompts.items()))
    return results
