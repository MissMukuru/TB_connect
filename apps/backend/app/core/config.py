from __future__ import annotations

from functools import lru_cache

from dotenv import find_dotenv, load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_name: str = "ShieldTB Kenya API"
    app_version: str = "0.1.0"
    api_prefix: str = "/api"

    supabase_url: str
    supabase_secret_key: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Allow running from `apps/backend/` while `.env` lives at repo root.
    env_path = find_dotenv(filename=".env", usecwd=True)
    if env_path:
        load_dotenv(env_path, override=False)

    return Settings(
        supabase_url=_env("SUPABASE_URL"),
        supabase_secret_key=_env("SUPABASE_SECRET_KEY"),
    )


def _env(name: str) -> str:
    import os

    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val

