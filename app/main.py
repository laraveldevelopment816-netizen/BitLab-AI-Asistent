"""
FastAPI aplikacija — entry point.

Sesija 1: skelet sa schemama i placeholder endpointima (vraćaju 501).
Sesija 2: implementacija /api/chat preko agenta + alata.
Sesija 3: /api/email i /api/tts.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import PROJECT_ROOT, settings


app = FastAPI(
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
    raise HTTPException(status_code=501, detail="Implementacija u Sesiji 2.")


@app.post("/api/email", response_model=EmailResponse)
async def api_email(req: EmailRequest) -> EmailResponse:
    """Endpoint koji n8n zove kad stigne novi email; vraća draft replyja."""
    raise HTTPException(status_code=501, detail="Implementacija u Sesiji 3.")


@app.post("/api/tts")
async def api_tts(req: TtsRequest):
    """Proxy ka ElevenLabs — primarna namjena: voice mod u browseru."""
    raise HTTPException(status_code=501, detail="Implementacija u Sesiji 3.")
