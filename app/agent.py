"""
Agent loop sa Claude tool use.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

import anthropic

from .config import settings
from .system_prompts import system_prompt
from .tools import ALL_TOOLS, dispatch


def _parse_voice_xml(text: str) -> tuple[str, str]:
    """Izvuci <text> i <voice> sekcije iz voice channel odgovora.

    Bug fix Sesija 8: kad Claude pošalje samo <voice>...</voice> blok bez
    obavezujućeg <text>...</text> wrappera, prijašnja verzija je vraćala
    cijeli original kao reply_text — što je značilo da raw <voice> tagovi
    cure u UI. Sad ako nema <text>, izvučemo sve **van** <voice> bloka."""
    text_m  = re.search(r'<text>(.*?)</text>',   text, re.DOTALL)
    voice_m = re.search(r'<voice>(.*?)</voice>', text, re.DOTALL)

    if text_m:
        reply_text = text_m.group(1).strip()
    elif voice_m:
        # Bez <text> wrappera, ali ima <voice> — sve van <voice> bloka
        # je primary tekst za chat. Ukloni voice blok da ne curi u UI.
        reply_text = re.sub(r'<voice>.*?</voice>', '', text, flags=re.DOTALL).strip()
        if not reply_text:
            # Edge: Claude poslao samo <voice> bez ičega prije/poslije —
            # koristi voice tekst kao fallback za reply
            reply_text = voice_m.group(1).strip()
    else:
        reply_text = text

    if voice_m:
        reply_voice = voice_m.group(1).strip()
    else:
        # Claude nije vratio <voice> tag — izvuci prve 2 rečenice čistog teksta
        raw = reply_text
        raw = re.sub(r'\*+', '', raw)
        raw = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', raw)
        raw = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', raw)
        raw = re.sub(r'#+\s*', '', raw)
        raw = re.sub(r'^\s*[-*]\s+', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'\s+', ' ', raw).strip()
        sentences = re.split(r'(?<=[.!?])\s+', raw)
        reply_voice = ' '.join(sentences[:2])

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


def _strip_voice_tags(text: str) -> str:
    """Defensive: ukloni curajuće <voice>/<text> XML tagove iz finalnog
    chat reply-ja. Idempotentno — ako Claude vrati clean output, no-op.

    Logika:
    - Ako postoji <text>...</text>, koristi sadržaj (Claude je ipak
      poštovao voice format, ali smo u chat channel-u — uzmi text dio)
    - Inače, ukloni <voice>...</voice> blok kompletno (sadržaj je za TTS,
      ne za UI)
    - Na kraju ukloni eventualne nepar otvorene/zatvorene tagove
    """
    text_m = re.search(r'<text>(.*?)</text>', text, re.DOTALL | re.IGNORECASE)
    if text_m:
        text = text_m.group(1)
    else:
        text = re.sub(r'<voice>.*?</voice>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'</?(?:voice|text)>', '', text, flags=re.IGNORECASE)
    return text.strip()


def _strip_horizontal_rules(text: str) -> str:
    """Defensive: ukloni standalone markdown horizontal rules (---/***/___).

    Sonnet 4.6 sa pojačanim promptom svejedno povremeno ubaci `---` separator
    između proizvoda ili kao footer. Frontend ne renderuje `<hr>` (chat
    balon je tijesan), pa to izlazi kao plain "---" tekst koji izgleda
    neprofesionalno. Idempotentan no-op kad output je već čist.

    Takođe normalizuje višestruke prazne redove (>2 \\n → 2)."""
    text = re.sub(r'^[ \t]*[-*_]{3,}[ \t]*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _default_model_for_channel(channel: str) -> str:
    return settings.email_model if channel == "email" else settings.chat_model


def run_agent(
    messages: list[dict[str, Any]],
    channel: str = "chat",
    model_override: str | None = None,
) -> dict[str, Any]:
    """
    Pokreće agent loop i vraća:
      reply, reply_voice, tools_used, escalated, iterations, _trace

    `_trace` je strukturirani log koji potroši dashboard storage:
      {model, tokens_in, tokens_out, latency_ms, tool_calls: [...]}
    """
    model = model_override or _default_model_for_channel(channel)
    sys_prompt = system_prompt(channel)
    client = _get_client()

    tools_used: list[str] = []
    escalated = False
    current_messages = list(messages)
    last_text = ""

    # Trace state — akumulirano po koraku
    trace_calls: list[dict[str, Any]] = []
    total_in = 0
    total_out = 0
    t_start = time.monotonic()

    for iteration in range(1, settings.max_tool_iterations + 1):
        response = client.messages.create(
            model=model,
            max_tokens=settings.max_output_tokens,
            system=sys_prompt,
            tools=ALL_TOOLS,
            messages=current_messages,
        )

        # Akumuliraj usage iz svakog API poziva
        usage = getattr(response, "usage", None)
        if usage is not None:
            total_in += getattr(usage, "input_tokens", 0) or 0
            total_out += getattr(usage, "output_tokens", 0) or 0

        # Izvuci tekst ako postoji u ovom odgovoru
        for block in response.content:
            if hasattr(block, "text"):
                last_text = block.text

        if response.stop_reason == "end_turn":
            return _finalize(
                last_text, channel, tools_used, escalated, iteration,
                model, total_in, total_out, t_start, trace_calls,
            )

        if response.stop_reason == "tool_use":
            current_messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tools_used.append(block.name)
                    if block.name == "escalate_to_human":
                        escalated = True
                    t_tool = time.monotonic()
                    result = dispatch(block.name, block.input)
                    tool_latency_ms = int((time.monotonic() - t_tool) * 1000)
                    trace_calls.append({
                        "iteration": iteration,
                        "tool_name": block.name,
                        "input_json": json.dumps(dict(block.input), ensure_ascii=False),
                        "output_text": result,
                        "latency_ms": tool_latency_ms,
                    })
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
    return _finalize(
        fallback, channel, tools_used, escalated, settings.max_tool_iterations,
        model, total_in, total_out, t_start, trace_calls,
    )


def _finalize(
    text: str,
    channel: str,
    tools_used: list[str],
    escalated: bool,
    iterations: int,
    model: str,
    total_in: int,
    total_out: int,
    t_start: float,
    trace_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Sklopi finalni response + trace dict."""
    if channel == "email":
        reply = _trim_email_preamble(text)
        reply_voice = ""
    elif channel == "voice":
        reply, reply_voice = _parse_voice_xml(text)
    else:
        reply = text
        reply_voice = ""

    # Defensive: NIKAD ne smije procuriti raw <voice>/<text> XML tag u UI.
    # Sesija 8 production bug: Sonnet povremeno pošalje <voice> blok čak i
    # u chat channel-u (jer se pravila o tagovima ne smiju curiti iz
    # VOICE_FORMAT prompt-a kad nije aktivan). Sanitizujemo na izlazu
    # bez obzira šta je channel rekao.
    reply = _strip_voice_tags(reply)
    # Sanitize horizontal rules + višestruke prazne redove (Sonnet 4.6
    # i sa pojačanim promptom u 20% slučajeva ubaci `---` footer).
    reply = _strip_horizontal_rules(reply)

    return {
        "reply": reply,
        "reply_voice": reply_voice,
        "tools_used": tools_used,
        "escalated": escalated,
        "iterations": iterations,
        "_trace": {
            "model": model,
            "tokens_in": total_in,
            "tokens_out": total_out,
            "latency_ms": int((time.monotonic() - t_start) * 1000),
            "tool_calls": trace_calls,
        },
    }
