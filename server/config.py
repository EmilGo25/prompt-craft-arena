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
    # How long a finished game's images stay fetchable (for the game-over recap
    # screen) before they're freed. Players sit on the summary screen after the
    # game ends; this is the grace window before those images are deleted.
    image_retention_seconds: int = 300

    # Global leaderboard (file-backed for now)
    leaderboard_path: str = "./data/leaderboard.json"

    # Objective pool: pre-generate target images off the request path so games
    # don't wait ~15-30s for a live draw. Disabled by default — turning it on
    # changes nothing functionally, it only makes game start faster (with a
    # live-draw fallback whenever the shelf is empty).
    objective_pool_enabled: bool = False
    objective_pool_target: int = 8      # desired ready images per difficulty
    objective_pool_floor: int = 3       # low watermark that triggers a refill
    objective_pool_max: int = 50        # hard ceiling per difficulty (cost seatbelt)
    objective_pool_concurrency: int = 4  # max simultaneous pre-generations
    objective_pool_refill_interval_seconds: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
