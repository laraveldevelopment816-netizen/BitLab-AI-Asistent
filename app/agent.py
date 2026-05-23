"""Minimalni agent — raw Anthropic poziv, prazan system prompt, bez tools.

TDD zero base: namjerno bez tool dispatch-a, bez sistem prompta. Eval će
pokazati šta nedostaje; dodaje se po potrebi."""

from __future__ import annotations

from typing import Any, cast

import anthropic
from anthropic.types import MessageParam

from .config import settings

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def run_agent(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Pošalji poruke Claude-u i vrati strukturisani odgovor.

    Trenutno: system="", tools=[]. Eval engine očekuje polja `reply`,
    `tool_calls`, `iterations` — vraćamo ih i sa praznim vrijednostima
    tako da downstream parser ne puca."""
    client = _get_client()
    response = client.messages.create(
        model=settings.chat_model,
        max_tokens=settings.max_output_tokens,
        system="",
        messages=cast("list[MessageParam]", messages),
    )
    reply = ""
    for block in response.content:
        if hasattr(block, "text"):
            reply = block.text
            break
    return {
        "reply": reply,
        "tool_calls": [],
        "iterations": 1,
    }
