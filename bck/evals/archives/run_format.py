"""
Eval: provjera da Claude (chat model) **u raw output-u** poštuje single-line
product format propisan u CHAT_FORMAT prompt-u.

Bez ovog evala ne možemo znati ko je krivac za razbijen layout — frontend
prepass (`collapseMultiLineProducts`) ili sam Claude. Cilj: ≥95% upita gdje
su proizvodi prikazani, RAW output sadrži ZERO `---` separatora i ZERO
multi-line product blokova. Defensive layer u widget-u je backstop, ne
norma.

Pokreni: python evals/run_format.py
Exit 0 ako pass-rate ≥ EVAL_THRESHOLD (default 0.95).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import anthropic

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402
from app.system_prompts import system_prompt  # noqa: E402
from app.tools import ALL_TOOLS, dispatch  # noqa: E402

EVAL_THRESHOLD = float(os.getenv("EVAL_THRESHOLD", "0.95"))

# Realni upiti koji garantovano triggeruju product results
QUERIES = [
    "Imate li laptop do 2000 KM",
    "Trebam 3 najbolja laptopa do 1500 KM",
    "Pokaži mi 5 monitora 27 inča",
    "Gaming miševi do 200 KM, pokaži 4 opcije",
    "Imate li tastature za office, max 5 modela",
]

# Single-line product regex — slika opciono, ime, cijena, dostupnost+link opciono
PROD_LINE_RE = re.compile(
    r'^\s*(?:[-*]\s+|\d+\.\s+)?'
    r'(?:!\[[^\]]*\]\(https?://[^)]+\)\s+)?'
    r'\*\*[^*]+\*\*'
    r'\s*[—–-]\s*[0-9][\d.,]*\s*KM'
    r'(?:\s*[—–-]\s*[^[\n]+?)?'
    r'(?:\s*[—–-]\s*\[[^\]]+\]\(https?://[^)]+\))?'
    r'\s*$',
    re.MULTILINE
)


def run_full_agent_loop(client, query: str) -> str:
    """Pokreni agent loop dok ne dođe do end_turn — vrati final text."""
    sys_prompt = system_prompt("chat")
    messages = [{"role": "user", "content": query}]
    last_text = ""

    for _ in range(5):
        resp = client.messages.create(
            model=settings.chat_model,
            max_tokens=settings.max_output_tokens,
            system=sys_prompt,
            tools=ALL_TOOLS,
            messages=messages,
        )
        for block in resp.content:
            if hasattr(block, "text"):
                last_text = block.text

        if resp.stop_reason == "end_turn":
            return last_text

        if resp.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type == "tool_use":
                    result = dispatch(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break
    return last_text


def analyze_format(raw: str) -> dict:
    """Vrati metrike za jedan raw Claude output:
       - has_products: bilo koja product-like linija postoji?
       - single_line_products: broj product linija u single-line formatu
       - multi_line_blocks: broj 'razbijenih' blokova (slika+ime+cijena u
         odvojenim redovima)
       - hr_separators: broj samostalnih `---` linija (van product cards)
       - voice_tags: broj <voice> tagova (ne smiju biti u chat reply-ju)
       - format_ok: True ako 0 multi_line_blocks i 0 hr_separators
    """
    single_line = len(PROD_LINE_RE.findall(raw))
    hr = len(re.findall(r'^\s*[-*_]{3,}\s*$', raw, re.MULTILINE))
    voice_tags = len(re.findall(r'</?voice>', raw, re.IGNORECASE))

    # Multi-line block detect: slika sama na liniji, sa bold ispod (sa ili
    # bez praznih redova između)
    multi = len(re.findall(
        r'!\[[^\]]*\]\(https?://[^)]+\)\s*\n+(?:[-*_]{3,}\s*\n+)?\s*\*\*[^*]',
        raw
    ))

    return {
        "has_products": single_line > 0 or multi > 0,
        "single_line_products": single_line,
        "multi_line_blocks": multi,
        "hr_separators": hr,
        "voice_tags": voice_tags,
        "format_ok": multi == 0 and hr == 0 and voice_tags == 0,
    }


def main() -> int:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    print(f"Eval format: {len(QUERIES)} upita · model={settings.chat_model} · threshold={EVAL_THRESHOLD:.0%}")
    print("─" * 80)

    passed = 0
    rows = []
    for i, q in enumerate(QUERIES, 1):
        try:
            raw = run_full_agent_loop(client, q)
        except Exception as exc:
            print(f"  {i}. ERROR  {q[:50]} → {exc}")
            rows.append({"query": q, "error": str(exc)})
            continue

        m = analyze_format(raw)
        ok = m["format_ok"]
        if ok:
            passed += 1
        tag = "✓" if ok else "✗"
        print(f"  {i}. {tag} {q[:50]:50s} | single={m['single_line_products']:>2}  multi={m['multi_line_blocks']}  hr={m['hr_separators']}  voice={m['voice_tags']}")
        if not ok:
            print(f"      RAW SAMPLE (first 400):\n      {raw[:400]!r}")
        rows.append({"query": q, **m})

    rate = passed / len(QUERIES) if QUERIES else 0
    print("─" * 80)
    print(f"Pass rate: {passed}/{len(QUERIES)} = {rate:.1%}  (threshold {EVAL_THRESHOLD:.0%})")
    return 0 if rate >= EVAL_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
