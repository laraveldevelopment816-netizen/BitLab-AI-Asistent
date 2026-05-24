"""Minimalni agent — LLM dispatch (PWR ili Anthropic) + tool use loop.

TDD zero base + memorija llm_backend_pwr_imperative:
- Default dispatch: PWR backend (LLM_BACKEND=pwr + PWR_API_KEY set u .env) —
  troši kredite od Claude pretplate kroz lokalni PlaywrightRouter
  (http://127.0.0.1:8765/v1). NE plaćeni Anthropic API.
- Fallback: Anthropic direktan API — samo ako PWR nije konfigurisan.

Tool use loop: oba runnera prosljeđuju `ALL_TOOLS_*` modelu, dispatch-uju
tool pozive kroz `app.tools.dispatch`, i kapsuliraju sve pozive u
`tool_calls` output liste (`[{"name", "args"}]`) koju eval framework
poredi sa očekivanjima iz `evals/sets/*.jsonl`.
"""

from __future__ import annotations

import json
from typing import Any, cast

import anthropic
import openai
from anthropic.types import MessageParam, ToolUseBlock
from openai.types.chat import ChatCompletionMessageFunctionToolCall

from .config import settings
from .tools import ALL_TOOLS_ANTHROPIC, ALL_TOOLS_OPENAI, dispatch

# Limit tool use iteracija da spriječi beskonačnu petlju ako model loop-uje.
# Hardcoded za Fazu 1 (jedan-dva tool poziva max po upitu); ako Faza 3+
# multi-tool sekvence trebaju više, premjesti u settings.
MAX_TOOL_ITERATIONS = 5

# Sistem prompt v1 — single source za OBA runnera (spec specs/categories.md §1, §3, §3.1).
# Anthropic put: prosljeđuje se kao `system=` parametar u messages.create().
# PWR put: prosljeđuje se kao prva poruka {"role": "system", "content": ...}.
# Refinement v1 dodaje out-of-scope ponašanje za negativni set (spec §4):
# kad upit ne odgovara nijednom katalogu (knjige, vrijeme, garancija) NE zovi tool.
SYSTEM_PROMPT_V1 = (
    "Ti si webshop agent za bitlab.rs. Kataloški domen: računarska oprema, "
    "mobilni uređaji, tableti, mrežna oprema, periferija — sve kategorije "
    "su izložene kroz `category_overview` i `search_products` tools.\n\n"
    "Pravila rutiranja:\n"
    "- Kad upit imenuje PARENT kategoriju iz mapping liste u "
    "`category_overview` description-u (npr. 'Računari', 'Printeri i skeneri'), "
    "pozovi `category_overview` sa odgovarajućim `category_id`.\n"
    "- Kad upit imenuje LEAF kategoriju iz mapping liste u `search_products` "
    "description-u (npr. 'Notebook', 'Tablet', 'Mobiteli') ILI traži konkretne "
    "proizvode/brendove unutar leaf-a, pozovi `search_products` sa odgovarajućim "
    "`category_id` (i opcionim `query`/`brand`/filter cijene ako su dati).\n"
    "- Ako upit ne odgovara nijednoj kategoriji iz catalog mapping-a "
    "(npr. 'knjige', 'namještaj', 'kakvo je vrijeme', 'garancija', 'reklamacija') "
    "ILI je dvosmislen bez jasnog category mapping-a, NE zovi tool — odgovori "
    "prirodno (kratko objasni da nije u katalogu ili traži pojašnjenje).\n"
    "- Ako upit izgleda kao typo (riječ slična kategoriji iz mapping liste, ali "
    "sa očiglednim greškama u slovima — npr. 'mobitejli', 'raunari', 'prnteri'), "
    "NE pretpostavljaj korekciju automatski i NE zovi tool — pitaj korisnika da "
    "pojasni koju kategoriju je tačno mislio.\n\n"
    "Output: ne objašnjavaj rutiranje — samo pozovi pravi tool ili odgovori "
    "tekstom kad je out-of-scope."
)

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

    Output shape: {reply: str, tool_calls: list[{name, args}], iterations: int}.
    """
    if _use_pwr():
        return _run_pwr(messages)
    return _run_anthropic(messages)


def _run_anthropic(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Anthropic SDK put — direktan API + tool use loop.

    Loop: dok je stop_reason='tool_use', dispatch-uj svaki tool blok i pošalji
    rezultate nazad u sljedećoj iteraciji. Pređemo li MAX_TOOL_ITERATIONS,
    vraćamo posljednji tekstualni odgovor (ili prazan string).
    """
    client = _get_anthropic_client()
    current: list[dict[str, Any]] = list(messages)
    captured_tool_calls: list[dict[str, Any]] = []
    reply = ""
    iteration = 0

    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1
        response = client.messages.create(
            model=settings.chat_model,
            max_tokens=settings.max_output_tokens,
            system=SYSTEM_PROMPT_V1,
            tools=cast(Any, ALL_TOOLS_ANTHROPIC),
            messages=cast("list[MessageParam]", current),
        )

        for block in response.content:
            if hasattr(block, "text") and getattr(block, "text", None):
                reply = block.text

        if response.stop_reason != "tool_use":
            break

        # Echo assistant response (uključuje tool_use blokove) nazad u messages.
        current.append({"role": "assistant", "content": response.content})

        tool_results: list[dict[str, Any]] = []
        for raw_block in response.content:
            # Runtime tag check umjesto isinstance — radi i sa MagicMock-om u
            # testovima; cast je samo za mypy narrowing.
            if getattr(raw_block, "type", None) != "tool_use":
                continue
            block = cast(ToolUseBlock, raw_block)
            args = dict(block.input) if isinstance(block.input, dict) else {}
            captured_tool_calls.append({"name": block.name, "args": args})
            result = dispatch(block.name, args)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                }
            )

        current.append({"role": "user", "content": tool_results})

    return {"reply": reply, "tool_calls": captured_tool_calls, "iterations": iteration}


def _run_pwr(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """PWR backend — OpenAI-kompatibilan endpoint + tool calls loop.

    Razlike u shape-u u odnosu na Anthropic:
    - Sistem prompt ide kao prva poruka {"role": "system", "content": "..."}.
    - Tool definicije u OpenAI shape (`type:"function"` wrapper).
    - Tool pozivi u `choice.message.tool_calls`, `function.arguments` je JSON
      string koji parsiramo nazad u dict.
    - finish_reason='tool_calls' (umjesto Anthropic 'tool_use').
    - Tool rezultati idu kao `{"role": "tool", "tool_call_id": ..., "content": ...}`.
    - Reasoning effort ide kroz extra_body (PWR-specific extension).
    """
    client = _get_pwr_client()
    pwr_messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT_V1}]
    pwr_messages.extend(messages)

    captured_tool_calls: list[dict[str, Any]] = []
    reply = ""
    iteration = 0

    while iteration < MAX_TOOL_ITERATIONS:
        iteration += 1
        response = client.chat.completions.create(
            model=settings.pwr_chat_model,
            messages=cast(Any, pwr_messages),
            max_tokens=settings.max_output_tokens,
            tools=cast(Any, ALL_TOOLS_OPENAI),
            extra_body={"reasoning_effort": settings.pwr_chat_model_effort},
        )

        if not response.choices:
            break
        choice = response.choices[0]
        msg = choice.message
        if msg.content:
            reply = msg.content

        if choice.finish_reason != "tool_calls":
            break

        # Echo assistant message (sa tool_calls) nazad — OpenAI protokol zahtijeva.
        # Filtriraj na function tool_calls (custom tools nisu podržani u Fazi 1).
        # Runtime check `tc.type == "function"` umjesto isinstance — radi sa
        # MagicMock testovima; cast samo za mypy narrowing.
        function_calls: list[ChatCompletionMessageFunctionToolCall] = [
            cast(ChatCompletionMessageFunctionToolCall, tc)
            for tc in (msg.tool_calls or [])
            if getattr(tc, "type", "function") == "function"
        ]
        tool_calls_echo = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in function_calls
        ]
        pwr_messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": tool_calls_echo,
            }
        )

        for tc in function_calls:
            try:
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                args = {}
            captured_tool_calls.append({"name": tc.function.name, "args": args})
            result = dispatch(tc.function.name, args)
            pwr_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                }
            )

    return {"reply": reply, "tool_calls": captured_tool_calls, "iterations": iteration}
