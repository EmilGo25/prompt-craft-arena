"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Image generation
    image_provider: Literal["stub", "fal"] = "stub"
    fal_key: str = ""

    # Judge
    judge: Literal["random", "claude"] = "random"
    anthropic_api_key: str = ""
    judge_model: str = "claude-opus-4-8"

    # Gameplay
    round_seconds: int = 30
    total_rounds: int = 5
    max_result_concurrency: int = 4

    # Room lifecycle
    empty_room_ttl_seconds: int = 120


@lru_cache
def get_settings() -> Settings:
    return Settings()
