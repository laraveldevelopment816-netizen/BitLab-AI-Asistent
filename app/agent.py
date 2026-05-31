"""Minimalni agent — LLM dispatch (PWR ili Anthropic) + forsiran tool use loop.

TDD zero base + memorija llm_backend_pwr_imperative:
- Default dispatch: PWR backend (LLM_BACKEND=pwr + PWR_API_KEY set u .env) —
  troši kredite od Claude pretplate kroz lokalni PlaywrightRouter
  (http://127.0.0.1:8765/v1). NE plaćeni Anthropic API.
- Fallback: Anthropic direktan API — samo ako PWR nije konfigurisan.

Forsiran tool use (`tool_choice` any/required): model na svaki upit zove tačno
jedan alat — kataloški (`category_overview`/`search_products`, dispatch kroz
`app.tools.dispatch`) ILI `respond_to_user` (finalni tekst). Time nema tihe
apstinencije ni halucinacije (uzrok iter17 regresije). `respond_to_user` se NE
kapsulira u `tool_calls` output (eval ga tretira kao "bez tool poziva"), pa
negativni upiti ostaju PASS. `tool_calls` (`[{"name","args"}]`) poredi se sa
očekivanjima iz `evals/sets/*.jsonl`.
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

# Sistem prompt — single source za OBA runnera. Lean leaf/parent logika uz
# forsiran tool use: model bira kataloški alat ILI respond_to_user, nikad
# slobodan tekst. (Zamijenio naduveni iter17 prompt koji je izazvao apstinenciju.)
SYSTEM_PROMPT_V1 = (
    "Ti si BitLab webshop asistent za bitlab.rs. Pomažeš korisnicima da nađu "
    "proizvode iz kataloga računarske i tehničke opreme.\n\n"
    "Na SVAKI upit moraš pozvati tačno jedan alat — nikad ne odgovaraj slobodnim "
    "tekstom direktno. Alati:\n"
    "- `category_overview(category_id)` — pregled potkategorija PARENT kategorije.\n"
    "- `search_products(category_id, query?, brand?, cijena?)` — pretraga u LEAF "
    "kategoriji ili po konkretnom proizvodu/brendu.\n"
    "- `respond_to_user(message)` — tekstualni odgovor korisniku: za upite van "
    "kataloga, dvosmislene/typo, i za finalni odgovor nakon tool rezultata.\n\n"
    "Pravila:\n"
    "1. NIKAD ne izmišljaj proizvode, cijene, dostupnost ni specifikacije — ni za "
    "poznate kategorije (monitori, telefoni, laptopi). Podatke dobijaš ISKLJUČIVO iz "
    "rezultata alata. Ako alat vrati prazno (`products: []`), kroz `respond_to_user` "
    "reci da trenutno nemaš podatke za tu kategoriju; NE nabrajaj modele, cijene ni "
    "URL-ove iz vlastitog znanja.\n"
    "2. Parent vs leaf:\n"
    "   - Gola PARENT kategorija bez kvalifikatora (npr. 'Mobiteli', 'Računari', "
    "'Printeri') → `category_overview` sa tim parent `category_id`.\n"
    "   - Kvalifikator (brend, model, cijena, namjena) ILI leaf kategorija ili "
    "konkretan proizvod → `search_products` sa odgovarajućim leaf `category_id`.\n"
    "   - LEAF PRIORITET: ako ime iz upita tačno odgovara LEAF kategoriji, biraj "
    "`search_products` za taj leaf i kad postoji sličan/isti PARENT. Posebno ovi su "
    "LEAF (→ `search_products`, NE parent `category_overview`): Mobilni telefoni, "
    "Kablovi, UPS, Televizori, Fotoaparati, Navigacije, USB uređaji, Kućanski aparati, "
    "Konzole.\n"
    "3. Upit van kataloga (knjige, namještaj, vrijeme, garancija, reklamacija), "
    "dvosmislen bez jasne kategorije, ili očigledan typo → `respond_to_user` sa "
    "kratkim tekstom (objasni ili traži pojašnjenje); NE zovi kataloške alate.\n"
    "4. Kad kataloški alat vrati rezultat, finalni odgovor korisniku uvijek šalji "
    "kroz `respond_to_user`.\n"
    "Jezik: BCS, latinica. Ton: kratko, direktno, bez fillera."
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
    """Anthropic put — forsiran tool use (`tool_choice={"type":"any"}`) + respond_to_user.

    Svaka iteracija forsira tool: model zove kataloški alat (dispatch, capture,
    nazad u petlju) ili `respond_to_user` (finalni tekst, van `captured_tool_calls`,
    break). `{"type":"any"}` je TVRDA garancija — nema tihe apstinencije.
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
            tool_choice=cast(Any, {"type": "any"}),
            messages=cast("list[MessageParam]", current),
        )
        current.append({"role": "assistant", "content": response.content})

        # Runtime tag check umjesto isinstance — radi i sa MagicMock-om u testovima.
        tool_uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        catalog = [b for b in tool_uses if getattr(b, "name", None) != "respond_to_user"]
        respond = next(
            (b for b in tool_uses if getattr(b, "name", None) == "respond_to_user"), None
        )

        if catalog:
            # Dispatch kataloških alata; svaki tool_use (uklj. respond) mora dobiti tool_result.
            tool_results: list[dict[str, Any]] = []
            for raw_block in tool_uses:
                block = cast(ToolUseBlock, raw_block)
                if block.name == "respond_to_user":
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": "OK"}
                    )
                    continue
                args = dict(block.input) if isinstance(block.input, dict) else {}
                captured_tool_calls.append({"name": block.name, "args": args})
                result = dispatch(block.name, args)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result}
                )
            current.append({"role": "user", "content": tool_results})
            continue

        if respond is not None:
            block = cast(ToolUseBlock, respond)
            reply = block.input.get("message", "") if isinstance(block.input, dict) else ""
            break

        # Nema tool_use (ne očekivano uz tool_choice=any) — fallback na tekst.
        for raw_block in response.content:
            if getattr(raw_block, "text", None):
                reply = raw_block.text
        break

    return {"reply": reply, "tool_calls": captured_tool_calls, "iterations": iteration}


def _run_pwr(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """PWR backend — forsiran tool use (`tool_choice="required"`) + respond_to_user.

    Isto kao Anthropic put, u OpenAI shape-u. PWR `required` je soft-enforcement
    (vidi STATUS "Poznata ograničenja"); ako model ne vrati tool, uzimamo
    `msg.content` kao reply.
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
            tool_choice=cast(Any, "required"),
            extra_body={"reasoning_effort": settings.pwr_chat_model_effort},
        )
        if not response.choices:
            break
        msg = response.choices[0].message

        function_calls: list[ChatCompletionMessageFunctionToolCall] = [
            cast(ChatCompletionMessageFunctionToolCall, tc)
            for tc in (msg.tool_calls or [])
            if getattr(tc, "type", "function") == "function"
        ]

        if not function_calls:
            # PWR soft-required nije ispoštovan — uzmi tekstualni odgovor.
            if msg.content:
                reply = msg.content
            break

        # Echo assistant message (sa tool_calls) — OpenAI protokol zahtijeva.
        pwr_messages.append(
            {
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
                    for tc in function_calls
                ],
            }
        )

        catalog = [tc for tc in function_calls if tc.function.name != "respond_to_user"]
        respond = next(
            (tc for tc in function_calls if tc.function.name == "respond_to_user"), None
        )

        if catalog:
            for tc in function_calls:
                if tc.function.name == "respond_to_user":
                    pwr_messages.append({"role": "tool", "tool_call_id": tc.id, "content": "OK"})
                    continue
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {}
                captured_tool_calls.append({"name": tc.function.name, "args": args})
                result = dispatch(tc.function.name, args)
                pwr_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue

        if respond is not None:
            try:
                args = json.loads(respond.function.arguments) if respond.function.arguments else {}
            except json.JSONDecodeError:
                args = {}
            reply = args.get("message", "") or ""
            break

    return {"reply": reply, "tool_calls": captured_tool_calls, "iterations": iteration}
