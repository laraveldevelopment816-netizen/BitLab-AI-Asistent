"""
FastAPI aplikacija — entry point.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import anthropic
import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import PROJECT_ROOT, settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload RAG indeks odmah (čisti numpy/json — brzo).
    # Embedding model se grije u BACKGROUND task-u — server ne čeka.
    # Razlog: na WSL2 /mnt/c sentence-transformers import traje ~50s. Bez ovoga
    # startup je minut+. Sa ovim, /healthz odgovara odmah, prvi /api/chat čeka model.
    import asyncio

    if settings.products_index.exists() and settings.products_meta.exists():
        from .rag import get_index
        idx = get_index()  # učitava .npz + meta.json — brzo
        asyncio.create_task(asyncio.to_thread(idx.preload_model))

    # Dashboard storage init — idempotentno
    from .storage.db import init_db
    await init_db()

    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    lifespan=lifespan,
    title="BitLab AI Asistent",
    description=(
        "Chat widget + Voice + Email auto-reply za webshop.bitlab.rs.\n\n"
        "Sva tri kanala dijele isti agent (Claude tool use) nad istom bazom znanja: "
        "5.287 proizvoda + FAQ."
    ),
    version="0.1.0",
)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Centralni safety net za Anthropic SDK greške koje ne uhvati call site
# (`app/agent.py` već lokalno hvata BadRequestError / RateLimitError /
# APIConnectionError). Ovdje pokrivamo ostatak: AuthenticationError,
# InternalServerError, generic APIStatusError, kao i mrežne greške ako bi
# preskočile lokalni handler. Cilj: pravi HTTP status + strukturirani log
# umjesto 500 sa raw stack trace-om.
def _is_quota_error(message: str) -> bool:
    msg = message.lower()
    return "credit balance" in msg or "billing" in msg or "quota" in msg


async def _anthropic_api_status_handler(
    request: Request, exc: anthropic.APIStatusError
) -> JSONResponse:
    logger.error(
        "Anthropic APIStatusError @ %s (status=%s): %s",
        request.url.path, getattr(exc, "status_code", "?"), exc,
        exc_info=True,
    )
    if _is_quota_error(str(exc)):
        return JSONResponse(
            status_code=402,
            content={
                "error": "ai_quota_exhausted",
                "reply": (
                    "Trenutno imamo tehnički zastoj sa AI sistemom. Molimo "
                    "kontaktirajte prodajni tim direktno:\n\n"
                    "📞 066 516 174 (Viber/tel)\n"
                    "✉️ prodaja@bitlab.rs"
                ),
            },
        )
    return JSONResponse(
        status_code=503,
        content={
            "error": "ai_unavailable",
            "reply": (
                "Žao mi je, AI servis privremeno nije dostupan. Pokušajte "
                "za par minuta ili nas kontaktirajte na 066 516 174."
            ),
        },
    )


async def _anthropic_connection_handler(
    request: Request, exc: anthropic.APIConnectionError
) -> JSONResponse:
    logger.error(
        "Anthropic APIConnectionError @ %s: %s",
        request.url.path, exc, exc_info=True,
    )
    return JSONResponse(
        status_code=503,
        content={
            "error": "ai_unavailable",
            "reply": "Mreža je trenutno preopterećena. Pokušajte ponovo za par sekundi.",
        },
    )


app.add_exception_handler(anthropic.APIStatusError, _anthropic_api_status_handler)
app.add_exception_handler(anthropic.APIConnectionError, _anthropic_connection_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dashboard router (logging + compare). Pod /api/dashboard/* sa bearer auth.
from .server.dashboard import router as dashboard_router  # noqa: E402

app.include_router(dashboard_router)


# ── Static (widget, voice demo) ──────────────────────────────
public_dir = PROJECT_ROOT / "public"
if public_dir.exists():
    app.mount("/public", StaticFiles(directory=public_dir), name="public")


# ── Schemas ──────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    channel: str = Field(default="chat", pattern="^(chat|voice|email)$")
    # UUID generisan klijent-side u widget.js — grupiše sve poruke jednog
    # razgovora pod jednu sesiju (Sessions tab u dashboard-u). Opciono za
    # backward compat sa starim klijentima.
    session_id: str | None = Field(default=None, max_length=36)


class ToolCallTrace(BaseModel):
    name: str
    input: dict
    # rezultat ne vraćamo klijentu — samo za interni log/eval


class ChatResponse(BaseModel):
    reply: str
    reply_voice: str = ""
    channel: str
    tools_used: list[str] = Field(default_factory=list)
    escalated: bool = False
    iterations: int = 0


class EmailRequest(BaseModel):
    sender: str = Field(..., max_length=200)
    subject: str = Field(..., max_length=500)
    body: str = Field(..., max_length=8000)


class EmailResponse(BaseModel):
    reply: str
    escalated: bool
    tools_used: list[str] = Field(default_factory=list)


class TtsRequest(BaseModel):
    text: str = Field(..., max_length=2000)
    voice_id: str | None = Field(default=None, max_length=100)


# ── Endpointi ────────────────────────────────────────────────


@app.get("/", include_in_schema=False)
async def root():
    """Widget demo stranica (kad je dostupna), inače redirect na /docs."""
    widget = public_dir / "widget.html"
    if widget.exists():
        return FileResponse(widget)
    return {"hint": "Otvori /docs za Swagger UI."}


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok",
        "chat_model": settings.chat_model,
        "email_model": settings.email_model,
        "embed_model": settings.embed_model,
        "products_index_present": settings.products_index.exists(),
        "products_meta_present": settings.products_meta.exists(),
        "faq_present": settings.faq_path.exists(),
    }


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def api_chat(request: Request, req: ChatRequest) -> ChatResponse:
    """Glavni endpoint — koristi se i iz widget-a i iz voice mode-a."""
    import asyncio
    from .agent import run_agent
    from .config import settings as _settings
    from .server.dashboard import _persist_trace

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    result = await asyncio.to_thread(run_agent, messages, req.channel)
    # Persist trace fire-and-forget — ne blokira response klijentu
    model = (result.get("_trace", {}) or {}).get("model") or _settings.chat_model
    asyncio.create_task(_persist_trace(
        channel=req.channel, model=model, prompt=req.message, result=result,
        session_id=req.session_id,
    ))
    return ChatResponse(
        reply=result["reply"],
        reply_voice=result.get("reply_voice", ""),
        channel=req.channel,
        tools_used=result["tools_used"],
        escalated=result["escalated"],
        iterations=result["iterations"],
    )


@app.post("/api/email", response_model=EmailResponse)
@limiter.limit("10/minute")
async def api_email(request: Request, req: EmailRequest) -> EmailResponse:
    """Endpoint koji n8n zove kad stigne novi email; vraća draft replyja."""
    import asyncio
    from .agent import run_agent
    from .config import settings as _settings
    from .server.dashboard import _persist_trace

    # Sklopi poruku sa kontekstom emaila.
    # Body se obavija u <email_body> tagove — system prompt nalaže Claude-u da
    # tekst između tagova tretira kao SADRŽAJ, ne instrukcije (prompt-injection
    # odbrana, vidi BITLAB_BASE pravilo 10 i EMAIL_FORMAT "Bezbjednost" sekciju).
    # Sanitizacija: ako korisnik proba zatvoriti tag prijevremeno, escape-ujemo.
    safe_body = req.body.strip().replace("</email_body>", "</email_body_>")
    message = (
        f"Email od: {req.sender}\n"
        f"Predmet: {req.subject}\n\n"
        f"<email_body>\n{safe_body}\n</email_body>"
    )
    result = await asyncio.to_thread(
        run_agent, [{"role": "user", "content": message}], "email",
    )
    model = (result.get("_trace", {}) or {}).get("model") or _settings.email_model
    asyncio.create_task(_persist_trace(
        channel="email", model=model, prompt=message, result=result,
    ))
    return EmailResponse(
        reply=result["reply"],
        escalated=result["escalated"],
        tools_used=result["tools_used"],
    )


_NUM_BCS = {
    0:"nula",1:"jedan",2:"dva",3:"tri",4:"četiri",5:"pet",6:"šest",7:"sedam",
    8:"osam",9:"devet",10:"deset",11:"jedanaest",12:"dvanaest",13:"trinaest",
    14:"četrnaest",15:"petnaest",16:"šesnaest",17:"sedamnaest",18:"osamnaest",
    19:"devetnaest",20:"dvadeset",30:"trideset",40:"četrdeset",50:"pedeset",
    60:"šezdeset",70:"sedamdeset",80:"osamdeset",90:"devedeset",
    100:"sto",200:"dvjesta",300:"trista",400:"četiristo",500:"petsto",
    600:"šesto",700:"sedamsto",800:"osamsto",900:"devetsto",
    1000:"hiljadu",2000:"dvije hiljade",3000:"tri hiljade",4000:"četiri hiljade",
}

def _n2w(n: int) -> str:
    if n in _NUM_BCS:
        return _NUM_BCS[n]
    if n < 100:
        return _NUM_BCS[n // 10 * 10] + " " + _NUM_BCS[n % 10]
    if n < 1000:
        h = _NUM_BCS.get(n // 100 * 100, str(n // 100) + " stotina")
        r = n % 100
        return (h + " " + _n2w(r)).strip() if r else h
    if n < 10000:
        t = _NUM_BCS.get(n // 1000 * 1000)
        if not t:
            t = _n2w(n // 1000) + " hiljada"
        r = n % 1000
        return (t + " " + _n2w(r)).strip() if r else t
    return str(n)

def _normalize_for_tts(text: str) -> str:
    """Pretvori cifre i skraćenice u oblik pogodan za govorni sintetizator."""
    import re

    # Ukloni emoji i Unicode simbole (TTS ih čita kao naziv karaktera)
    text = re.sub(
        "[\U0001F000-\U0001FFFF"
        "\U00002702-\U000027B0"
        "\U0001F900-\U0001F9FF"
        "☀-➿"
        "⌀-⏿"
        "︀-️"
        "]+",
        "", text
    )

    # Cijene: "1.450,00 KM" / "1.936 KM" / "389,00 KM" / "389.00 KM" / "389 KM"
    # Bug fix Sesija 8: u BCS formatu "1.936 KM" tačka je separator hiljada,
    # ne decimalni. Prije fix-a int(float("1.936")) = 1, pa TTS čita
    # "jedna marka" umjesto "hiljadu devetsto trideset šest maraka".
    def _price(m):
        raw = m.group(1)
        if "." in raw and "," in raw:
            # Evropski format sa centima: 1.450,00 → 1450.00
            raw = raw.replace(".", "").replace(",", ".")
        elif "." in raw and "," not in raw:
            # Tačka bez zareza — tipično separator hiljada (1.936) ili
            # decimalna (3.50GHz, ali ovdje smo u KM kontekstu).
            # Heuristika: ako se sve grupe nakon prve tačke imaju tačno
            # 3 cifre, to je separator hiljada → ukloni tačke. Inače
            # ostavi kao decimalni.
            parts = raw.split(".")
            if all(len(p) == 3 for p in parts[1:]) and len(parts[0]) <= 3:
                raw = raw.replace(".", "")
            # else: ostavi raw, float() će ga parse-ovati kao decimalni
        elif "," in raw and raw.index(",") == len(raw) - 3:
            # 389,00 → 389.00
            raw = raw.replace(",", ".")
        try:
            val = int(float(raw))
        except ValueError:
            return m.group(0)
        suffix = "maraka" if val != 1 else "marka"
        return _n2w(val) + " " + suffix
    text = re.sub(r'(\d[\d.,]*\d|\d)\s*KM\b', _price, text)

    # Veličine: "16GB", "1TB", "512MB", "3.5GHz"
    units = {"GB": "gigabajta", "TB": "terabajta", "MB": "megabajta",
             "GHz": "gigaherca", "MHz": "megaherca"}
    for abbr, word in units.items():
        def _unit(m, w=word):
            try:
                v = float(m.group(1).replace(",", "."))
                iv = int(v)
                return (_n2w(iv) if v == iv else m.group(1)) + " " + w
            except Exception:
                return m.group(0)
        text = re.sub(r'(\d+(?:[.,]\d+)?)\s*' + abbr + r'\b', _unit, text)

    # Ostale gole cifre > 9 (npr. redni brojevi, godine) — ostavi kao je
    # Ukloni markdown ostatke
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # [tekst](url) → tekst
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)       # slike ukloni
    text = re.sub(r'#+\s*', '', text)                       # headings
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)  # bullet points

    return text.strip()


def _normalize_rate(rate: str) -> str:
    """Normalizuj TTS rate u format koji Azure SSML i edge-tts strogo zahtijevaju.
    Mora imati eksplicitni + ili - i % na kraju (npr. '+0%', '-10%', '+15%').
    "0%", "0", "" → "+0%". "10%" → "+10%". "-15%" → "-15%".
    """
    if not rate or not str(rate).strip():
        return "+0%"
    s = str(rate).strip().replace(" ", "")
    if not s.endswith("%"):
        s += "%"
    if not (s.startswith("+") or s.startswith("-")):
        s = "+" + s
    return s


# Voice off (chat-only deploy) — STATUS kartica vmoff.
# Reaktivacija = ukloni komentar na dekoratorima ispod.
# @app.post("/api/tts")
# @limiter.limit("20/minute")
async def api_tts(request: Request, req: TtsRequest):
    """TTS — fallback chain:
       1. Azure Speech Services (oficijalno, sa AZURE_SPEECH_KEY)
       2. edge-tts (free, koristi iste Azure neural glasove neoficijalno)
    """
    import io
    import edge_tts
    import xml.sax.saxutils as _sx

    tts_text = _normalize_for_tts(req.text)
    rate = _normalize_rate(settings.tts_rate)

    # Voice se očekuje u Microsoft formatu (npr. "hr-HR-GabrijelaNeural").
    requested = (req.voice_id or "").strip()
    voice = requested if "-" in requested else settings.tts_voice

    # ── Azure Speech Services (primarno kad je ključ postavljen) ──
    if settings.azure_speech_key:
        try:
            xml_lang = "-".join(voice.split("-")[:2])
            ssml = (
                f'<speak version="1.0" xml:lang="{xml_lang}">'
                f'<voice name="{voice}">'
                f'<prosody rate="{rate}">{_sx.escape(tts_text)}</prosody>'
                f'</voice></speak>'
            )
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://{settings.azure_speech_region}.tts.speech.microsoft.com/cognitiveservices/v1",
                    headers={
                        "Ocp-Apim-Subscription-Key": settings.azure_speech_key,
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
                        "User-Agent": "BitLab-AI-Asistent",
                    },
                    content=ssml.encode("utf-8"),
                )
            if resp.status_code == 200 and resp.content:
                return Response(content=resp.content, media_type="audio/mpeg")
            print(f"[TTS] Azure failed: {resp.status_code} {resp.text[:200]!r}")
        except Exception as e:
            print(f"[TTS] Azure exception: {e!r}")

    # ── edge-tts (final fallback — uvijek dostupno bez ključa) ──
    try:
        buf = io.BytesIO()
        communicate = edge_tts.Communicate(tts_text, voice, rate=rate)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        audio_data = buf.read()
        if audio_data:
            return Response(content=audio_data, media_type="audio/mpeg")
        print("[TTS] edge-tts returned empty audio")
    except Exception as e:
        print(f"[TTS] edge-tts exception: {e!r}")

    raise HTTPException(status_code=503, detail="TTS provideri nedostupni. Pokušaj ponovo.")


# Voice off (chat-only deploy) — STATUS kartica vmoff.
# Reaktivacija = ukloni komentar na dekoratorima ispod.
# @app.post("/api/stt")
# @limiter.limit("20/minute")
async def api_stt(request: Request, audio: UploadFile = File(...)):
    """Transkribuje audio preko Groq Whisper API-ja. Vraća {text, language, provider="groq"}.
    Ako Groq nije dostupan (no key, network, invalid key, non-200), vraća HTTP 503.
    Pre-flight check: GET /api/voice/status (widget zove ovo prije pokretanja voice mode-a).
    """
    _MAX_AUDIO = 25 * 1_048_576  # 25 MB
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > _MAX_AUDIO:
        raise HTTPException(status_code=413, detail="Audio fajl prevelik (max 25 MB).")

    data = await audio.read()
    if len(data) > _MAX_AUDIO:
        raise HTTPException(status_code=413, detail="Audio fajl prevelik (max 25 MB).")
    suffix = ".webm"
    if audio.content_type:
        if "ogg" in audio.content_type:
            suffix = ".ogg"
        elif "wav" in audio.content_type:
            suffix = ".wav"

    # Poznate Whisper halucinacije na tišini / tihu audio
    _HALLUCINATIONS = {
        "hvala", "hvala vam", "hvala ti", "hvala lijepo", "hvala puno",
        "zahvaljujem", "zahvaljujem vam", "thank you", "thanks",
        "mersi", "merci", "pretplatite se", "lajkujte",
        ".", "..", "...", " ",
    }

    def _clean_stt(text: str) -> str:
        t = text.strip()
        return "" if t.lower() in _HALLUCINATIONS else t

    # Groq Whisper-large-v3 — JEDINI STT provider.
    # Ako pukne, vraćamo 503 i widget gasi voice button (vidi /api/voice/status).
    # Domain hint pomaže Whisper-u za IT termine i lokalna imena.
    _DOMAIN_HINT = (
        "Razgovor sa BitLab prodajnim asistentom o IT opremi u Banja Luci. "
        "Klijent pita za laptop, računar, monitor, SSD, RAM, GPU, miš, tastaturu, "
        "slušalice, gaming opremu. Brendovi: ASUS, Lenovo, HP, Dell, MSI, Acer, "
        "Intel, AMD, NVIDIA, Samsung, Kingston, Crucial, Logitech, Razer. "
        "Cijene se daju u markama (KM), npr. 'do hiljadu maraka', 'oko 500 KM'. "
        "Pita se i o dostavi, garanciji, plaćanju, MKD ratama, B2B fakturama."
    )

    if not settings.groq_api_key:
        logger.warning("STT pozvan a GROQ_API_KEY nije postavljen")
        raise HTTPException(status_code=503, detail="Voice nije dostupan")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                files={"file": (f"audio{suffix}", data, audio.content_type or "audio/webm")},
                data={
                    "model": settings.groq_whisper_model,
                    "language": "hr",
                    "response_format": "json",
                    "prompt": _DOMAIN_HINT,
                    "temperature": "0",
                },
            )
    except Exception as e:
        logger.warning("Groq STT zahtjev pukao: %r", e)
        raise HTTPException(status_code=503, detail="Voice nije dostupan")

    if resp.status_code != 200:
        logger.warning("Groq STT HTTP %s: %s", resp.status_code, resp.text[:200])
        raise HTTPException(status_code=503, detail="Voice nije dostupan")

    text = _clean_stt(resp.json().get("text", ""))
    # Prazno = tišina ili poznata halucinacija — nije error, samo no-speech
    return {"text": text, "language": "hr", "provider": "groq"}


# ── Voice availability check (pre-flight za widget) ─────────────
_voice_health: dict = {"checked_at": 0.0, "ok": False, "reason": "uninitialized"}
_VOICE_HEALTH_TTL = 60.0  # sekundi


# Voice off (chat-only deploy) — STATUS kartica vmoff.
# Reaktivacija = ukloni komentar na dekoratoru ispod.
# @app.get("/api/voice/status")
async def api_voice_status() -> dict:
    """Pre-flight check za voice mode. Widget zove ovo na load i prikazuje
    voice button samo ako je `voice_available: true`. Cache-uje rezultat 60s
    da ne udara Groq sa svakim browser refresh-om."""
    import time
    now = time.time()

    if not settings.groq_api_key:
        return {"voice_available": False, "reason": "no_api_key"}

    # Cache hit
    if now - _voice_health["checked_at"] < _VOICE_HEALTH_TTL:
        return {"voice_available": _voice_health["ok"], "reason": _voice_health["reason"]}

    # Cache miss — ping Groq /v1/models (cheap GET, ~200 byte response)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
            )
    except Exception as e:
        _voice_health.update(checked_at=now, ok=False, reason="groq_unreachable")
        logger.warning("Voice status check failed: %r", e)
        return {"voice_available": False, "reason": "groq_unreachable"}

    if resp.status_code == 200:
        _voice_health.update(checked_at=now, ok=True, reason="ok")
        return {"voice_available": True, "reason": "ok"}

    reason = f"groq_http_{resp.status_code}"
    _voice_health.update(checked_at=now, ok=False, reason=reason)
    logger.warning("Voice status: Groq returned %s", resp.status_code)
    return {"voice_available": False, "reason": reason}
