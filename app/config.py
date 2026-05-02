"""Centralizovan env loader (Pydantic Settings)."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
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

    @field_validator("anthropic_api_key")
    @classmethod
    def _require_api_key(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "ANTHROPIC_API_KEY nije postavljen u .env. "
                "Dodaj: ANTHROPIC_API_KEY=sk-ant-..."
            )
        return v
    chat_model: str = "claude-haiku-4-5-20251001"
    email_model: str = "claude-sonnet-4-6"
    max_tool_iterations: int = 5
    max_output_tokens: int = 1024

    # ── Embeddings (lokalno, sentence-transformers) ───────────
    embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embed_dim: int = 384  # za MiniLM-L12-v2

    # ── TTS glas (edge-tts default) ───────────────────────────
    # Opcije za BCS: bs-BA-VesnaNeural, bs-BA-GoranNeural,
    #   hr-HR-GabrijelaNeural, sr-RS-SophieNeural, sr-RS-NicholasNeural
    tts_voice: str = "hr-HR-GabrijelaNeural"
    tts_rate: str = "+15%"

    # ── ElevenLabs (opcionalno) ───────────────────────────────
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None
    elevenlabs_model: str = "eleven_multilingual_v2"

    # ── Azure Speech Services — preferirani TTS + STT za bs/hr/sr ───
    # Free tier (uvijek besplatno): 500K znakova/mjesec Neural TTS,
    #                                5h/mjesec STT.
    # Setup: portal.azure.com → "Speech Services" → Keys & Endpoint.
    # Region npr. "westeurope", "swedencentral", "germanywestcentral".
    azure_speech_key: str | None = None
    azure_speech_region: str = "westeurope"
    # Jezik koji Azure STT očekuje (hr-HR pokriva i bs/sr Latinica dovoljno dobro).
    azure_stt_language: str = "hr-HR"

    # ── Groq Whisper (opcionalno — besplatno 7200s/dan) ───────
    groq_api_key: str | None = None
    groq_whisper_model: str = "whisper-large-v3-turbo"

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
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["https://webshop.bitlab.rs", "http://localhost:8000"]
    )


settings = Settings()
