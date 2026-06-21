"""Minimalna FastAPI app — boot + widget + raw /api/chat + rate-limit handlers.

TDD zero base + memorija anthropic_budget + EVAL_OPTIMIZACIJA review:
Bez exception handler-a za RateLimitError, FastAPI default ih guta kao 500
'Internal Server Error', što znači da eval client ne prepoznaje rate limit
pa runner ne može da snima checkpoint. Ova dva handler-a mapiraju oba
SDK exceptiona (openai + anthropic) u 429 sa porukom u body-ju."""

from __future__ import annotations

import asyncio

import anthropic
import openai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
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


@app.exception_handler(openai.RateLimitError)
async def _openai_rate_limit_handler(_request: Request, exc: openai.RateLimitError) -> JSONResponse:
    """PWR (openai SDK) rate limit → 429 sa rate_limit oznakom u detail-u."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"rate_limit: {exc}"},
    )


@app.exception_handler(anthropic.RateLimitError)
async def _anthropic_rate_limit_handler(
    _request: Request, exc: anthropic.RateLimitError
) -> JSONResponse:
    """Anthropic SDK rate limit → 429 sa rate_limit oznakom u detail-u."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"rate_limit: {exc}"},
    )


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
