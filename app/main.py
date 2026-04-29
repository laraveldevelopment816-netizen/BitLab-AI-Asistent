"""
FastAPI aplikacija — entry point.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
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
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    channel: str = Field(default="chat", pattern="^(chat|voice|email)$")


class ToolCallTrace(BaseModel):
    name: str
    input: dict
    # rezultat ne vraćamo klijentu — samo za interni log/eval


class ChatResponse(BaseModel):
    reply: str
    channel: str
    tools_used: list[str] = Field(default_factory=list)
    escalated: bool = False
    iterations: int = 0


class EmailRequest(BaseModel):
    sender: str
    subject: str
    body: str


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


@app.post("/api/tts")
async def api_tts(req: TtsRequest):
    """Proxy ka ElevenLabs TTS API-ju — API ključ ostaje na serveru."""
    if not settings.elevenlabs_api_key or settings.elevenlabs_api_key == "sk_...":
        raise HTTPException(status_code=503, detail="ElevenLabs nije konfigurisan (ELEVENLABS_API_KEY).")

    voice_id = req.voice_id or settings.elevenlabs_voice_id
    if not voice_id:
        raise HTTPException(status_code=503, detail="Voice ID nije postavljen (ELEVENLABS_VOICE_ID).")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": settings.elevenlabs_api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": req.text,
                "model_id": settings.elevenlabs_model,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.3,
                    "use_speaker_boost": True,
                },
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"ElevenLabs greška: {resp.status_code}")

    return Response(content=resp.content, media_type="audio/mpeg")
