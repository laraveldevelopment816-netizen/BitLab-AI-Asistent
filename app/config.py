"""Minimalni config — API keys + chat model + LLM backend dispatch.

TDD zero base + memorija llm_backend_pwr_imperative: default backend je PWR
(lokalni PlaywrightRouter, troši kredite od Claude pretplate); Anthropic
direktan API je fallback samo ako PWR nije konfigurisan."""

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

    # Anthropic (fallback put — ne preporučeno za produkciju)
    anthropic_api_key: str = ""
    chat_model: str = "claude-sonnet-4-6"
    max_output_tokens: int = 1024

    # LLM backend selector — vidi memoriju llm_backend_pwr_imperative.
    # "pwr": lokalni PlaywrightRouter (OpenAI-kompatibilan), troši pretplatu.
    # "anthropic": direktan Anthropic API (fallback, plaćeno).
    llm_backend: str = "anthropic"
    pwr_api_key: str = ""
    pwr_base_url: str = "http://127.0.0.1:8765/v1"
    pwr_chat_model: str = "claude-sonnet-4-6"
    pwr_chat_model_effort: str = "low"  # "low" | "medium" | "high"


settings = Settings()
