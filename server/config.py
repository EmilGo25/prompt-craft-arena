"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI (used for both image generation and the LLM judge)
    openai_api_key: str = ""

    # Image generation
    image_provider: Literal["stub", "openai"] = "stub"
    openai_image_model: str = "gpt-image-1"  # or gpt-image-1.5 / gpt-image-2
    openai_image_size: str = "1024x1024"

    # Judge
    judge: Literal["random", "openai"] = "random"
    judge_model: str = "gpt-4o"  # vision + structured outputs (json_schema)

    # Gameplay
    round_seconds: int = 60
    total_rounds: int = 5
    max_result_concurrency: int = 4
    # Target difficulty: easy | medium | hard | ramp (ramp = easy→hard across rounds)
    target_difficulty: Literal["easy", "medium", "hard", "ramp"] = "medium"

    # Room lifecycle
    empty_room_ttl_seconds: int = 120

    # Global leaderboard (file-backed for now)
    leaderboard_path: str = "./data/leaderboard.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
