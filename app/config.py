"""Minimalni config — Anthropic API key + chat model.

TDD zero base: postojeća poslovna logika je u bck/. Dodavati polja
SAMO kad failing eval to traži."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    anthropic_api_key: str = ""
    chat_model: str = "claude-sonnet-4-6"
    max_output_tokens: int = 1024


settings = Settings()
