"""Wiring tests for the pluggable image/judge providers.

These only check that the builders construct the right object for each provider
and reject unknown ones — no network calls. The local providers (drawthings /
ollama) build their clients eagerly but only hit the network on use.
"""

import pytest

from server.services.image_gen import (
    DrawThingsImageGenerator,
    StubImageGenerator,
    build_image_generator,
)
from server.services.judge import OpenAIJudge, RandomJudge, build_judge


def test_build_image_generator_stub_and_drawthings():
    assert isinstance(build_image_generator("stub"), StubImageGenerator)

    gen = build_image_generator(
        "drawthings", drawthings_api_base="http://localhost:7860/", drawthings_size="768x512"
    )
    assert isinstance(gen, DrawThingsImageGenerator)
    # Trailing slash trimmed; size parsed into width/height.
    assert gen._api_base == "http://localhost:7860"
    assert (gen._width, gen._height) == (768, 512)


def test_drawthings_bad_size_falls_back():
    gen = DrawThingsImageGenerator(size="not-a-size")
    assert (gen._width, gen._height) == (1024, 1024)


def test_build_image_generator_unknown_raises():
    with pytest.raises(ValueError):
        build_image_generator("nope")


def test_build_judge_random_and_ollama():
    assert isinstance(build_judge("random"), RandomJudge)

    judge = build_judge("ollama", ollama_base_url="http://localhost:11434/v1", ollama_model="qwen2.5vl:7b")
    assert isinstance(judge, OpenAIJudge)
    # Local path uses the portable json_object response format.
    assert judge._structured == "json_object"
    assert judge._model == "qwen2.5vl:7b"
    assert judge._response_format() == {"type": "json_object"}


def test_build_judge_unknown_raises():
    with pytest.raises(ValueError):
        build_judge("nope")
