"""Image generation behind a pluggable interface.

This is the one place that talks to an external image model. The
``StubImageGenerator`` renders the prompt text onto a deterministic colored card
with Pillow, so the entire game runs offline with no API keys.
``OpenAIImageGenerator`` calls OpenAI's image API (gpt-image-1).
``DrawThingsImageGenerator`` calls a *local* A1111-compatible HTTP server (Draw
Things, AUTOMATIC1111, Forge, ...) so open-weight models (FLUX.1, SDXL) can run
fully on-device with no API keys.
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


# ---------------------------------------------------------------------------
# Draw Things / A1111-compatible local server (open-weight models)
# ---------------------------------------------------------------------------


class DrawThingsImageGenerator:
    """Generates via a local A1111-compatible ``/sdapi/v1/txt2img`` endpoint.

    Works with Draw Things' built-in HTTP server (``localhost:7860`` by default)
    and with any AUTOMATIC1111 / Forge / SD.Next WebUI exposing the same API.
    Whichever open-weight model is loaded in that server (FLUX.1-schnell, SDXL,
    ...) is what gets used — we only send the prompt, dimensions, step count, and
    optional seed. No API key, nothing leaves the machine.
    """

    def __init__(
        self,
        *,
        api_base: str = "http://localhost:7860",
        steps: int = 4,
        size: str = "1024x1024",
        negative_prompt: str = "",
    ) -> None:
        self._api_base = api_base.rstrip("/")
        self._steps = steps
        self._negative = negative_prompt
        try:
            w_str, h_str = size.lower().split("x")
            self._width, self._height = int(w_str), int(h_str)
        except ValueError:
            self._width, self._height = 1024, 1024

    async def generate(self, prompt: str, *, seed: int | None = None) -> GeneratedImage:
        import httpx  # lazy: stub path needs no HTTP client at runtime

        payload: dict[str, object] = {
            "prompt": prompt,
            "negative_prompt": self._negative,
            "steps": self._steps,
            "width": self._width,
            "height": self._height,
        }
        if seed is not None:
            payload["seed"] = seed
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(f"{self._api_base}/sdapi/v1/txt2img", json=payload)
            resp.raise_for_status()
            data = resp.json()
        b64 = data["images"][0]
        # Some servers return a full data URL; keep only the base64 payload.
        if "," in b64[:64]:
            b64 = b64.split(",", 1)[1]
        return GeneratedImage(image_bytes=base64.b64decode(b64), content_type="image/png")


def build_image_generator(
    provider: str,
    *,
    openai_api_key: str = "",
    openai_image_model: str = "gpt-image-1",
    openai_image_size: str = "1024x1024",
    drawthings_api_base: str = "http://localhost:7860",
    drawthings_steps: int = 4,
    drawthings_size: str = "1024x1024",
) -> ImageGenerator:
    if provider == "openai":
        return OpenAIImageGenerator(
            openai_api_key, model=openai_image_model, size=openai_image_size
        )
    if provider == "drawthings":
        return DrawThingsImageGenerator(
            api_base=drawthings_api_base,
            steps=drawthings_steps,
            size=drawthings_size,
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
