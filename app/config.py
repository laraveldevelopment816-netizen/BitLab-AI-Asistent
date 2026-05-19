"""Centralizovan env loader (Pydantic Settings)."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Effort niveau po kanalu — utiče na Anthropic thinking budget ili
# PWR reasoning_effort. Default je "low" da Anthropic produkcijski put
# (bez thinking-a) ostane nepromijenjen za default vrijednosti.
EffortLevel = Literal["low", "medium", "high"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── LLM backend selector ─────────────────────────────────
    # "anthropic" (default, produkcija): direktan Anthropic API.
    # "pwr": rutiranje kroz PlaywrightRouter (paušal Pro/Copilot pretplate);
    #   pwr_base_url + pwr_api_key obavezni. Vidi
    #   playwright-router/docs/api-examples.md sekcija 11 za ugovor.
    llm_backend: Literal["anthropic", "pwr"] = "anthropic"

    # ── Anthropic ─────────────────────────────────────────────
    anthropic_api_key: str = Field(default="")
    # Sesija 8 hotfix: Haiku ne sluša "ne pitaj pojašnjenje" pravilo
    # za upite sa typoom (npr. "lapatovoe" → tražio pojašnjenje umjesto
    # search-a, čak je u sledećoj iteraciji halucinirao "nema laptopa").
    # Sonnet 4.6 robusno hvata namjeru i kroz typoove. Vidi
    # tests/test_typo_robustness.py i evals/category_eval.json (typo cases).
    chat_model: str = "claude-sonnet-4-6"
    chat_model_effort: EffortLevel = "low"
    email_model: str = "claude-sonnet-4-6"
    email_model_effort: EffortLevel = "low"
    # Voice kanal koristi chat_model + chat_model_effort (nije zasebno polje).
    max_tool_iterations: int = 5
    max_output_tokens: int = 1024

    # ── PlaywrightRouter (test backend, vidi PWR docs sek. 11) ───
    pwr_base_url: str = "http://127.0.0.1:8765/v1"
    pwr_api_key: str = ""
    # Kroz PWR koristimo Claude Code CLI varijantu (~15s latencija,
    # paušal Pro pretplate) umjesto web UI ("claude", ~30s).
    pwr_chat_model: str = "claude-sonnet-4-6"
    pwr_chat_model_effort: EffortLevel = "low"
    pwr_email_model: str = "claude-sonnet-4-6"
    pwr_email_model_effort: EffortLevel = "low"

    @model_validator(mode="after")
    def _validate_backend_credentials(self) -> "Settings":
        if self.llm_backend == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY nije postavljen u .env. "
                "Dodaj: ANTHROPIC_API_KEY=sk-ant-... "
                "(ili postavi LLM_BACKEND=pwr za PWR test backend)."
            )
        if self.llm_backend == "pwr" and not self.pwr_api_key:
            raise ValueError(
                "PWR_API_KEY nije postavljen u .env. "
                "Vidi playwright-router/.env za API_KEY vrijednost."
            )
        return self

    # ── Embeddings (lokalno, sentence-transformers) ───────────
    embed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embed_dim: int = 384  # za MiniLM-L12-v2

    # ── TTS glas (Azure / edge-tts) ───────────────────────────
    # Opcije za BCS: bs-BA-VesnaNeural, bs-BA-GoranNeural,
    #   hr-HR-GabrijelaNeural, sr-RS-SophieNeural, sr-RS-NicholasNeural
    tts_voice: str = "hr-HR-GabrijelaNeural"
    tts_rate: str = "+15%"

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

    # Eskalacija notifikacija — ako popunjeno, escalate_to_human tool
    # šalje email na ovu adresu. Default je smtp_user (sami sebi).
    # Bez SMTP config-a, tool vraća "upit zabilježen" umjesto laži
    # "tim obaviješten".
    escalation_email_to: str | None = None

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

    # ── Dashboard / logging (Sesija 8) ────────────────────────
    # Bearer token za /api/dashboard/*. Bez ključa endpointi vraćaju 401.
    # Generiši: python -c "import secrets; print(secrets.token_urlsafe(32))"
    dashboard_api_key: str | None = None
    # Mapa "short-name -> full Anthropic model id" — koristi se za
    # POST /api/dashboard/compare {"models": ["haiku","sonnet"]}.
    @property
    def model_registry(self) -> dict[str, str]:
        return {
            "haiku": self.chat_model,
            "sonnet": self.email_model,
        }


settings = Settings()
