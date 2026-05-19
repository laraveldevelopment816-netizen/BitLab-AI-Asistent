"""
Agent loop sa Claude tool use.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

import anthropic
import openai

from .config import settings
from .system_prompts import system_prompt
from .tools import ALL_TOOLS, ALL_TOOLS_OPENAI_SHAPE, dispatch


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

_anthropic_client: anthropic.Anthropic | None = None
_pwr_client: openai.OpenAI | None = None


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


# Markdown table line: | foo | bar | ili | --- | --- | (separator row)
_MD_TABLE_LINE = re.compile(r'^\s*\|.*\|\s*$')


def _strip_markdown_tables(text: str) -> str:
    """Defensive: ukloni markdown tabele (`| col | col |`).

    Voice channel demo bug: Sonnet je vratio listu laptopa kao markdown
    tabelu. Frontend renderer ne podržava tabele — pipe karakteri se
    vide u tekstu, a TTS izgovara "crta crta crta" za separator row.
    PROD_RE traži single-line bullet format pa tabela postaje šum.

    Strategija: detektuj 2+ uzastopne tabele linije, ukloni ih iz
    output-a. NE pokušava da konvertuje u list (rizik gubitka podataka).
    Pojačan prompt je primarna obrana, ovo je backstop."""
    lines = text.split('\n')
    out: list[str] = []
    i = 0
    while i < len(lines):
        if _MD_TABLE_LINE.match(lines[i]):
            # Provjeri da li sledeći red takođe table — minimum 2 reda za pravu tabelu
            if i + 1 < len(lines) and _MD_TABLE_LINE.match(lines[i + 1]):
                # Preskoči sve uzastopne table line-ove
                while i < len(lines) and _MD_TABLE_LINE.match(lines[i]):
                    i += 1
                continue
        out.append(lines[i])
        i += 1
    return '\n'.join(out).strip()


def _default_model_for_channel(channel: str, backend: str | None = None) -> str:
    backend = backend or settings.llm_backend
    if backend == "pwr":
        return settings.pwr_email_model if channel == "email" else settings.pwr_chat_model
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
      {model, tokens_in, tokens_out, latency_ms, via_pwr, tool_calls: [...]}

    Backend selekcija prema `settings.llm_backend`:
      - "anthropic" (default, produkcija): direktan Anthropic API.
      - "pwr": PlaywrightRouter (paušal pretplate; usage tokens uvijek 0).
    """
    backend = settings.llm_backend
    model = model_override or _default_model_for_channel(channel, backend)
    sys_prompt = system_prompt(channel)

    if backend == "pwr":
        return _run_pwr(messages, channel, model, sys_prompt)
    return _run_anthropic(messages, channel, model, sys_prompt)


def _run_anthropic(
    messages: list[dict[str, Any]],
    channel: str,
    model: str,
    sys_prompt: str,
) -> dict[str, Any]:
    client = _get_anthropic_client()

    tools_used: list[str] = []
    escalated = False
    current_messages = list(messages)
    last_text = ""

    trace_calls: list[dict[str, Any]] = []
    total_in = 0
    total_out = 0
    t_start = time.monotonic()

    for iteration in range(1, settings.max_tool_iterations + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=settings.max_output_tokens,
                system=sys_prompt,
                tools=ALL_TOOLS,
                messages=current_messages,
            )
        except anthropic.BadRequestError as exc:
            err_msg = str(exc)
            print(f"[AGENT] Anthropic 400: {err_msg}")
            if "credit balance" in err_msg.lower() or "billing" in err_msg.lower():
                ui_msg = (
                    "Trenutno imamo tehnički zastoj sa AI sistemom. Molimo "
                    "kontaktirajte prodajni tim direktno:\n\n"
                    "📞 066 516 174 (Viber/tel)\n✉️ prodaja@bitlab.rs"
                )
                voice_msg = (
                    "Trenutno imamo tehnički zastoj. Molim vas kontaktirajte "
                    "prodajni tim na 066 516 174."
                )
            else:
                ui_msg = (
                    "Žao mi je, AI servis privremeno nije dostupan. "
                    "Pokušajte za par minuta ili nas kontaktirajte na "
                    "066 516 174."
                )
                voice_msg = (
                    "AI servis privremeno nije dostupan. Pokušajte za par minuta."
                )
            return _graceful_return(channel, ui_msg, voice_msg, tools_used, escalated,
                                     iteration, model, total_in, total_out, t_start, trace_calls,
                                     via_pwr=False)
        except (anthropic.RateLimitError, anthropic.APIConnectionError) as exc:
            print(f"[AGENT] Anthropic transient: {type(exc).__name__}: {exc}")
            ui_msg = "Mreža je trenutno preopterećena. Pokušajte ponovo za par sekundi."
            return _graceful_return(channel, ui_msg, ui_msg, tools_used, escalated,
                                     iteration, model, total_in, total_out, t_start, trace_calls,
                                     via_pwr=False)

        usage = getattr(response, "usage", None)
        if usage is not None:
            total_in += getattr(usage, "input_tokens", 0) or 0
            total_out += getattr(usage, "output_tokens", 0) or 0

        for block in response.content:
            if hasattr(block, "text"):
                last_text = block.text

        if response.stop_reason == "end_turn":
            return _finalize(
                last_text, channel, tools_used, escalated, iteration,
                model, total_in, total_out, t_start, trace_calls, via_pwr=False,
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
        model, total_in, total_out, t_start, trace_calls, via_pwr=False,
    )


def _run_pwr(
    messages: list[dict[str, Any]],
    channel: str,
    model: str,
    sys_prompt: str,
) -> dict[str, Any]:
    """PWR backend (OpenAI-kompatibilan endpoint). Razlike u odnosu na Anthropic:

    - `system` ide kao prva poruka u `messages` (ne kao zaseban param).
    - tool_calls dolaze u choices[0].message.tool_calls, arguments je JSON string.
    - tool_result je `{"role":"tool","tool_call_id":...,"content":...}`.
    - finish_reason: "stop" (end_turn ekv.) / "tool_calls" (tool_use ekv.).
    - `usage.total_tokens` uvijek 0 — Claude.ai web ne izlaže brojeve. Trace
       nosi `via_pwr=True` da UI prikaže "paušal" umjesto cijene.
    - Streaming sa tools nije podržano (HTTP 400) — pozivamo bez `stream=`.
    """
    client = _get_pwr_client()

    tools_used: list[str] = []
    escalated = False
    last_text = ""

    pwr_messages: list[dict[str, Any]] = [{"role": "system", "content": sys_prompt}]
    pwr_messages.extend(messages)

    trace_calls: list[dict[str, Any]] = []
    t_start = time.monotonic()

    for iteration in range(1, settings.max_tool_iterations + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=pwr_messages,
                tools=ALL_TOOLS_OPENAI_SHAPE,
                max_tokens=settings.max_output_tokens,
            )
        except openai.BadRequestError as exc:
            print(f"[AGENT/PWR] BadRequest: {exc}")
            ui_msg = (
                "Žao mi je, AI servis privremeno nije dostupan. "
                "Pokušajte za par minuta ili nas kontaktirajte na 066 516 174."
            )
            voice_msg = "AI servis privremeno nije dostupan. Pokušajte za par minuta."
            return _graceful_return(channel, ui_msg, voice_msg, tools_used, escalated,
                                     iteration, model, 0, 0, t_start, trace_calls,
                                     via_pwr=True)
        except (openai.RateLimitError, openai.APIConnectionError) as exc:
            print(f"[AGENT/PWR] transient: {type(exc).__name__}: {exc}")
            ui_msg = "Mreža je trenutno preopterećena. Pokušajte ponovo za par sekundi."
            return _graceful_return(channel, ui_msg, ui_msg, tools_used, escalated,
                                     iteration, model, 0, 0, t_start, trace_calls,
                                     via_pwr=True)
        except openai.APIStatusError as exc:
            print(f"[AGENT/PWR] status {exc.status_code}: {exc}")
            ui_msg = (
                "Žao mi je, AI servis privremeno nije dostupan. "
                "Pokušajte za par minuta ili nas kontaktirajte na 066 516 174."
            )
            voice_msg = "AI servis privremeno nije dostupan. Pokušajte za par minuta."
            return _graceful_return(channel, ui_msg, voice_msg, tools_used, escalated,
                                     iteration, model, 0, 0, t_start, trace_calls,
                                     via_pwr=True)

        choice = response.choices[0]
        msg = choice.message
        if msg.content:
            last_text = msg.content

        if choice.finish_reason == "stop":
            return _finalize(
                last_text, channel, tools_used, escalated, iteration,
                model, 0, 0, t_start, trace_calls, via_pwr=True,
            )

        if choice.finish_reason == "tool_calls":
            pwr_messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in (msg.tool_calls or [])
                ],
            })

            for tc in msg.tool_calls or []:
                tool_name = tc.function.name
                try:
                    tool_input = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    tool_input = {}
                tools_used.append(tool_name)
                if tool_name == "escalate_to_human":
                    escalated = True
                t_tool = time.monotonic()
                result = dispatch(tool_name, tool_input)
                tool_latency_ms = int((time.monotonic() - t_tool) * 1000)
                trace_calls.append({
                    "iteration": iteration,
                    "tool_name": tool_name,
                    "input_json": json.dumps(tool_input, ensure_ascii=False),
                    "output_text": result,
                    "latency_ms": tool_latency_ms,
                })
                pwr_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            break

    fallback = last_text or (
        "Žao mi je, trenutno ne mogu odgovoriti. "
        "Kontaktirajte nas na Viber 066 516 174 ili prodaja@bitlab.rs."
    )
    return _finalize(
        fallback, channel, tools_used, escalated, settings.max_tool_iterations,
        model, 0, 0, t_start, trace_calls, via_pwr=True,
    )


def _graceful_return(
    channel: str, ui_msg: str, voice_msg: str,
    tools_used: list[str], escalated: bool, iterations: int,
    model: str, total_in: int, total_out: int, t_start: float,
    trace_calls: list[dict[str, Any]],
    via_pwr: bool = False,
) -> dict[str, Any]:
    """Vrati strukturisanu fallback poruku kad LLM nije dostupan.
    Za voice channel, voice_msg ide u TTS (bez emojija/URL-ova)."""
    return {
        "reply": ui_msg,
        "reply_voice": voice_msg if channel == "voice" else "",
        "tools_used": tools_used,
        "escalated": escalated,
        "iterations": iterations,
        "_trace": {
            "model": model, "tokens_in": total_in, "tokens_out": total_out,
            "latency_ms": int((time.monotonic() - t_start) * 1000),
            "via_pwr": via_pwr,
            "tool_calls": trace_calls,
        },
    }


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
    via_pwr: bool = False,
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
    # Sanitize markdown tabele — frontend renderer ih ne podržava, a
    # TTS čita pipe + crtice. Voice channel demo bug.
    reply = _strip_markdown_tables(reply)

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
            "via_pwr": via_pwr,
            "tool_calls": trace_calls,
        },
    }
