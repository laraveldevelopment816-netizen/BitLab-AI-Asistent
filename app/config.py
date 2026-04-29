"""Centralizovan env loader (Pydantic Settings)."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Anthropic ─────────────────────────────────────────────
    anthropic_api_key: str = Field(default="")
    chat_model: str = "claude-haiku-4-5-20251001"
    email_model: str = "claude-sonnet-4-6"
    max_tool_iterations: int = 5
    max_output_tokens: int = 1024

    # ── Embeddings (lokalno, sentence-transformers) ───────────
    embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embed_dim: int = 384  # za MiniLM-L12-v2

    # ── ElevenLabs ────────────────────────────────────────────
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None
    elevenlabs_model: str = "eleven_multilingual_v2"

    # ── Email (rezerva ako n8n cloud zataji) ──────────────────
    imap_host: str | None = None
    imap_port: int = 993
    imap_user: str | None = None
    imap_password: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None

    # ── Webshop ───────────────────────────────────────────────
    webshop_base_url: str = "https://webshop.bitlab.rs"
    product_url_template: str = "https://webshop.bitlab.rs/proizvod/{urlhash}"

    # ── Putanje ───────────────────────────────────────────────
    data_dir: Path = PROJECT_ROOT / "data"
    products_json: Path = PROJECT_ROOT / "data" / "all-products.json"
    products_index: Path = PROJECT_ROOT / "data" / "products.index.npz"
    products_meta: Path = PROJECT_ROOT / "data" / "products.meta.json"
    faq_path: Path = PROJECT_ROOT / "data" / "faq.md"

    # ── CORS ──────────────────────────────────────────────────
    allowed_origins: list[str] = Field(default_factory=lambda: ["*"])


settings = Settings()
