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

    # ── OpenClaw gateway (opt-in, single source of truth) ─────
    # When use_openclaw=True, chat-only path routes via OpenClaw gateway
    # using local Claude CLI subscription (no ANTHROPIC_API_KEY needed).
    # NOTE: tool-use (product search, escalation) is NOT yet wired through
    # OpenClaw — direct Anthropic path remains the production tool path.
    use_openclaw: bool = False
    openclaw_base_url: str = "http://127.0.0.1:18789/v1"
    openclaw_api_key: str = ""
    openclaw_model: str = "openclaw/default"

    # ── Anthropic ─────────────────────────────────────────────
    anthropic_api_key: str = Field(default="")

    @field_validator("anthropic_api_key")
    @classmethod
    def _require_api_key(cls, v: str, info) -> str:
        if not v and not info.data.get("use_openclaw"):
            raise ValueError(
                "ANTHROPIC_API_KEY nije postavljen u .env. "
                "Dodaj: ANTHROPIC_API_KEY=sk-ant-... "
                "(ili postavi USE_OPENCLAW=true za routing kroz gateway)"
            )
        return v
    # Sesija 8 hotfix: Haiku ne sluša "ne pitaj pojašnjenje" pravilo
    # za upite sa typoom (npr. "lapatovoe" → tražio pojašnjenje umjesto
    # search-a, čak je u sledećoj iteraciji halucinirao "nema laptopa").
    # Sonnet 4.6 robusno hvata namjeru i kroz typoove. Vidi
    # tests/test_typo_robustness.py i evals/category_eval.json (typo cases).
    chat_model: str = "claude-sonnet-4-6"
    email_model: str = "claude-sonnet-4-6"
    opus_model: str = "claude-opus-4-7"
    max_tool_iterations: int = 5
    max_output_tokens: int = 1024

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
            "opus": self.opus_model,
        }


settings = Settings()
