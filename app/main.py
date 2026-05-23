"""Minimalna FastAPI app — boot + widget + raw /api/chat.

TDD zero base: nema dashboard-a, nema email/voice, nema RAG warmup-a,
nema exception handler-a koji ovise od poslovne logike. Sve to je u
bck/. Dodavati natrag SAMO kad failing eval to traži."""
from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import run_agent
from .config import PROJECT_ROOT

app = FastAPI(title="BitLab AI Asistent — TDD zero base", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

public_dir = PROJECT_ROOT / "public"
if public_dir.exists():
    app.mount("/public", StaticFiles(directory=public_dir), name="public")


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=20000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


@app.get("/", include_in_schema=False)
async def root():
    widget = public_dir / "widget.html"
    if widget.exists():
        return FileResponse(widget)
    return {"hint": "Otvori /docs za Swagger UI."}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})
    result = await asyncio.to_thread(run_agent, messages)
    return result
