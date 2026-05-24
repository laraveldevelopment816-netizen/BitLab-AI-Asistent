"""Minimalni agent — LLM dispatch (PWR ili Anthropic) sa praznim system, bez tools.

TDD zero base + memorija llm_backend_pwr_imperative:
- Default dispatch: PWR backend (LLM_BACKEND=pwr + PWR_API_KEY set u .env) —
  troši kredite od Claude pretplate kroz lokalni PlaywrightRouter
  (http://127.0.0.1:8765/v1). NE plaćeni Anthropic API.
- Fallback: Anthropic direktan API — samo ako PWR nije konfigurisan.

Eval će pokazati šta nedostaje od tools; dodaje se SAMO na zahtjev failing eval-a.
Kad se dodaju tools — moraju biti definisani u OBA runnera (_run_anthropic i
_run_pwr) sa odgovarajućim shape-om (Anthropic vs OpenAI tool format)."""

from __future__ import annotations

from typing import Any, cast

import anthropic
import openai
from anthropic.types import MessageParam

from .config import settings

_anthropic_client: anthropic.Anthropic | None = None
_pwr_client: openai.OpenAI | None = None


def _use_pwr() -> bool:
    """True ako LLM_BACKEND=pwr i PWR_API_KEY je setovan."""
    return settings.llm_backend == "pwr" and bool(settings.pwr_api_key)


def _get_anthropic_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


def _get_pwr_client() -> openai.OpenAI:
    global _pwr_client
    if _pwr_client is None:
        _pwr_client = openai.OpenAI(
            base_url=settings.pwr_base_url,
            api_key=settings.pwr_api_key,
        )
    return _pwr_client


def run_agent(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Pošalji poruke aktivnom LLM backend-u i vrati strukturisani odgovor.

    Dispatch (memorija llm_backend_pwr_imperative):
    - LLM_BACKEND=pwr + PWR_API_KEY postavljen → _run_pwr (lokalni router).
    - inače → _run_anthropic (direktan Anthropic API, fallback).

    Output shape: {reply: str, tool_calls: list, iterations: int}.
    """
    if _use_pwr():
        return _run_pwr(messages)
    return _run_anthropic(messages)


def _run_anthropic(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Anthropic SDK put — direktan API poziv."""
    client = _get_anthropic_client()
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
    return {"reply": reply, "tool_calls": [], "iterations": 1}


def _run_pwr(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """PWR backend — OpenAI-kompatibilan endpoint (PlaywrightRouter).

    Razlike u shape-u u odnosu na Anthropic:
    - Sistem prompt ide kao prva poruka {"role": "system", "content": "..."}.
    - Response je response.choices[0].message.content (string),
      ne response.content lista blokova.
    - Reasoning effort prosljeđujemo kroz extra_body (PWR-specific extension).
    """
    client = _get_pwr_client()
    openai_messages: list[dict[str, Any]] = [{"role": "system", "content": ""}]
    openai_messages.extend(messages)
    response = client.chat.completions.create(
        model=settings.pwr_chat_model,
        messages=cast(Any, openai_messages),
        max_tokens=settings.max_output_tokens,
        extra_body={"reasoning_effort": settings.pwr_chat_model_effort},
    )
    reply = ""
    if response.choices and response.choices[0].message.content:
        reply = response.choices[0].message.content
    return {"reply": reply, "tool_calls": [], "iterations": 1}
