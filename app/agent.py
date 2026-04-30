"""
Agent loop sa Claude tool use.
"""
from __future__ import annotations

from typing import Any

import anthropic

from .config import settings
from .system_prompts import system_prompt
from .tools import ALL_TOOLS, dispatch

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _trim_email_preamble(text: str) -> str:
    """Odsjeci sve prije 'Poštovani' ako Claude doda uvodne komentare."""
    marker = "Poštovani"
    idx = text.find(marker)
    return text[idx:] if idx != -1 else text


def run_agent(
    messages: list[dict[str, Any]],
    channel: str = "chat",
) -> dict[str, Any]:
    """
    Pokreće agent loop i vraća:
      reply, tools_used, escalated, iterations
    """
    model = settings.email_model if channel == "email" else settings.chat_model
    sys_prompt = system_prompt(channel)
    client = _get_client()

    tools_used: list[str] = []
    escalated = False
    current_messages = list(messages)
    last_text = ""

    for iteration in range(1, settings.max_tool_iterations + 1):
        response = client.messages.create(
            model=model,
            max_tokens=settings.max_output_tokens,
            system=sys_prompt,
            tools=ALL_TOOLS,
            messages=current_messages,
        )

        # Izvuci tekst ako postoji u ovom odgovoru
        for block in response.content:
            if hasattr(block, "text"):
                last_text = block.text

        if response.stop_reason == "end_turn":
            reply = _trim_email_preamble(last_text) if channel == "email" else last_text
            return {
                "reply": reply,
                "tools_used": tools_used,
                "escalated": escalated,
                "iterations": iteration,
            }

        if response.stop_reason == "tool_use":
            current_messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tools_used.append(block.name)
                    if block.name == "escalate_to_human":
                        escalated = True
                    result = dispatch(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            current_messages.append({"role": "user", "content": tool_results})
        else:
            break

    # Max iteracija dostignut ili neočekivan stop_reason
    return {
        "reply": last_text or (
            "Žao mi je, trenutno ne mogu odgovoriti na vaš upit. "
            "Kontaktirajte nas na Viber 066 516 174 ili prodaja@bitlab.rs."
        ),
        "tools_used": tools_used,
        "escalated": escalated,
        "iterations": settings.max_tool_iterations,
    }
