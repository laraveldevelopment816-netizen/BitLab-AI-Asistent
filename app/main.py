"""
FastAPI aplikacija — entry point.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import PROJECT_ROOT, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload RAG indeks i embedding model pri startu da bi prvi upit bio brz
    if settings.products_index.exists() and settings.products_meta.exists():
        from .rag import get_index
        idx = get_index()
        idx.preload_model()
    yield


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


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    text: str
    voice_id: str | None = None


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
async def api_chat(req: ChatRequest) -> ChatResponse:
    """Glavni endpoint — koristi se i iz widget-a i iz voice mode-a."""
    from .agent import run_agent

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    result = run_agent(messages, channel=req.channel)
    return ChatResponse(
        reply=result["reply"],
        reply_voice=result.get("reply_voice", ""),
        channel=req.channel,
        tools_used=result["tools_used"],
        escalated=result["escalated"],
        iterations=result["iterations"],
    )


@app.post("/api/email", response_model=EmailResponse)
async def api_email(req: EmailRequest) -> EmailResponse:
    """Endpoint koji n8n zove kad stigne novi email; vraća draft replyja."""
    from .agent import run_agent

    # Sklopi poruku sa kontekstom emaila
    message = (
        f"Email od: {req.sender}\n"
        f"Predmet: {req.subject}\n\n"
        f"{req.body.strip()}"
    )
    result = run_agent(
        [{"role": "user", "content": message}],
        channel="email",
    )
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

    # Cijene: "1.450,00 KM" / "389,00 KM" / "389.00 KM" / "389 KM"
    def _price(m):
        raw = m.group(1)
        # Evropski format: 1.450,00 → ukloni točku-hiljade, zamijeni zarez s točkom
        if "." in raw and "," in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw and raw.index(",") == len(raw) - 3:
            raw = raw.replace(",", ".")  # 389,00 → 389.00
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


@app.post("/api/tts")
async def api_tts(req: TtsRequest):
    """TTS via edge-tts (Microsoft Azure neuralni glasovi, bez API ključa).
    Fallback: ElevenLabs ako je ELEVENLABS_API_KEY konfigurisan i radi.
    """
    import io
    import edge_tts

    voice = req.voice_id or settings.elevenlabs_voice_id or settings.tts_voice
    tts_text = _normalize_for_tts(req.text)

    # Ako je to ElevenLabs voice ID format (ne sadrži '-'), pokušaj ElevenLabs
    if settings.elevenlabs_api_key and "-" not in voice:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice}",
                    headers={
                        "xi-api-key": settings.elevenlabs_api_key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                    json={
                        "text": tts_text,
                        "model_id": settings.elevenlabs_model,
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                            "style": 0.3,
                            "use_speaker_boost": True,
                        },
                    },
                )
            if resp.status_code == 200:
                return Response(content=resp.content, media_type="audio/mpeg")
        except Exception:
            pass  # ElevenLabs nedostupan, padamo na edge-tts

    # edge-tts — Microsoft Azure neuralni glas, besplatno, bez API ključa
    edge_voice = voice if "-" in voice else settings.tts_voice
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(tts_text, edge_voice, rate=settings.tts_rate)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return Response(content=buf.read(), media_type="audio/mpeg")


# ── Whisper STT ──────────────────────────────────────────────
_whisper_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # "small" model: ~150MB, dobar za BCS; "tiny" brži ali slabiji
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    return _whisper_model


@app.post("/api/stt")
async def api_stt(audio: UploadFile = File(...)):
    """Transkribuje audio. Koristi Groq Whisper API ako je GROQ_API_KEY postavljen,
    inače lokalni faster-whisper. Vraća {text, language, provider}.
    """
    import tempfile, os
    from asyncio import get_event_loop

    data = await audio.read()
    suffix = ".webm"
    if audio.content_type:
        if "ogg" in audio.content_type:
            suffix = ".ogg"
        elif "wav" in audio.content_type:
            suffix = ".wav"

    # ── Groq Whisper (brži, bolji, besplatno 7200s/dan) ──────────
    if settings.groq_api_key:
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
                    },
                )
            if resp.status_code == 200:
                return {"text": resp.json().get("text", "").strip(), "language": "hr", "provider": "groq"}
        except Exception:
            pass  # Groq nedostupan, fallback na lokalni

    # ── Lokalni faster-whisper (fallback) ─────────────────────────
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        loop = get_event_loop()
        model = await loop.run_in_executor(None, _get_whisper)
        segments, info = await loop.run_in_executor(
            None,
            lambda: model.transcribe(tmp_path, language="hr", beam_size=5),
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
    finally:
        os.unlink(tmp_path)

    return {"text": text, "language": info.language, "provider": "local"}
