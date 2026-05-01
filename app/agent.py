"""
Agent loop sa Claude tool use.
"""
from __future__ import annotations

import re
from typing import Any

import anthropic

from .config import settings
from .system_prompts import system_prompt
from .tools import ALL_TOOLS, dispatch


def _parse_voice_xml(text: str) -> tuple[str, str]:
    """Izvuci <text> i <voice> sekcije iz voice channel odgovora."""
    text_m  = re.search(r'<text>(.*?)</text>',   text, re.DOTALL)
    voice_m = re.search(r'<voice>(.*?)</voice>', text, re.DOTALL)
    reply_text  = text_m.group(1).strip()  if text_m  else text
    reply_voice = voice_m.group(1).strip() if voice_m else text
    return reply_text, reply_voice

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
            if channel == "email":
                raw = _trim_email_preamble(last_text)
                return {"reply": raw, "reply_voice": "", "tools_used": tools_used, "escalated": escalated, "iterations": iteration}
            if channel == "voice":
                reply_text, reply_voice = _parse_voice_xml(last_text)
                return {"reply": reply_text, "reply_voice": reply_voice, "tools_used": tools_used, "escalated": escalated, "iterations": iteration}
            return {
                "reply": last_text,
                "reply_voice": "",
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

    fallback = last_text or (
        "Žao mi je, trenutno ne mogu odgovoriti. "
        "Kontaktirajte nas na Viber 066 516 174 ili prodaja@bitlab.rs."
    )
    if channel == "voice":
        reply_text, reply_voice = _parse_voice_xml(fallback)
        return {"reply": reply_text, "reply_voice": reply_voice, "tools_used": tools_used, "escalated": escalated, "iterations": settings.max_tool_iterations}
    return {"reply": fallback, "reply_voice": "", "tools_used": tools_used, "escalated": escalated, "iterations": settings.max_tool_iterations}
