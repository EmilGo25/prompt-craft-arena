"""Image generation behind a pluggable interface.

Claude cannot generate images, so this is the one place that talks to an
external image model. The ``StubImageGenerator`` renders the prompt text onto a
deterministic colored card with Pillow, so the entire game runs offline with no
API keys. ``FalImageGenerator`` calls fal.ai FLUX-schnell over HTTP.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import textwrap
from dataclasses import dataclass
from typing import Protocol

import httpx
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
# fal.ai FLUX-schnell
# ---------------------------------------------------------------------------


class FalImageGenerator:
    """Calls fal.ai FLUX-schnell. Needs FAL_KEY. ~1-2s per image."""

    ENDPOINT = "https://fal.run/fal-ai/flux/schnell"

    def __init__(self, api_key: str, *, image_size: str = "square") -> None:
        if not api_key:
            raise ValueError("FalImageGenerator requires a fal.ai API key")
        self._api_key = api_key
        self._image_size = image_size

    async def generate(self, prompt: str, *, seed: int | None = None) -> GeneratedImage:
        payload: dict[str, object] = {
            "prompt": prompt,
            "image_size": self._image_size,
            "num_images": 1,
        }
        if seed is not None:
            payload["seed"] = seed
        headers = {"Authorization": f"Key {self._api_key}"}
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(self.ENDPOINT, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            url = data["images"][0]["url"]
            img = await client.get(url)
            img.raise_for_status()
            content_type = img.headers.get("content-type", "image/png")
            return GeneratedImage(image_bytes=img.content, content_type=content_type)


def build_image_generator(provider: str, *, fal_key: str = "") -> ImageGenerator:
    if provider == "fal":
        return FalImageGenerator(fal_key)
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
