"""
Eval: gleda da li Claude (chat model) ispravno klasifikuje korisnikov upit
u `category_id` parametar `search_products` toola u prvoj iteraciji.

Pass: prvi tool_use blok je `search_products` sa `category_id == expected`.
Fail: bez tool_use, drugi tool, missing/wrong category_id.

Pokreni: python evals/run_categories.py
Exit code 0 ako pass-rate ≥ EVAL_THRESHOLD (default 0.80), inače 1.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anthropic

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402
from app.system_prompts import system_prompt  # noqa: E402
from app.tools import ALL_TOOLS, CATEGORIES  # noqa: E402

EVAL_PATH = PROJECT_ROOT / "evals" / "category_eval.json"
EVAL_THRESHOLD = float(os.getenv("EVAL_THRESHOLD", "0.80"))


def _eval_one(client: anthropic.Anthropic, query: str) -> dict:
    """Vrati {category_id, tool_name, ok_tool} iz prvog Claude odgovora."""
    resp = client.messages.create(
        model=settings.chat_model,
        max_tokens=300,  # samo prvi tool_use, ne treba puno
        system=system_prompt("chat"),
        tools=ALL_TOOLS,
        messages=[{"role": "user", "content": query}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return {
                "tool_name": block.name,
                "category_id": block.input.get("category_id") if block.name == "search_products" else None,
                "ok_tool": block.name == "search_products",
            }
    return {"tool_name": None, "category_id": None, "ok_tool": False}


def main() -> int:
    if not EVAL_PATH.exists():
        print(f"Nema {EVAL_PATH}", file=sys.stderr)
        return 1

    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    passed = 0
    failed_rows: list[tuple[str, str, str | None, str | None]] = []
    print(f"Eval: {len(cases)} upita · model={settings.chat_model} · threshold={EVAL_THRESHOLD:.0%}")
    print("─" * 80)

    for i, case in enumerate(cases, 1):
        q = case["query"]
        expected = case["expected_category_id"]
        try:
            r = _eval_one(client, q)
        except Exception as exc:
            print(f"  {i:2}. ERROR  {q[:60]} → {exc}")
            failed_rows.append((q, expected, None, f"exc: {exc}"))
            continue

        got = r["category_id"]
        match = (got == expected)
        if match:
            passed += 1
            tag = "✓"
        else:
            tag = "✗"
            expected_label = CATEGORIES.get(expected, {}).get("label", "?")
            got_label = CATEGORIES.get(got or "", {}).get("label", "—") if got else "(none)"
            failed_rows.append((q, f"{expected} ({expected_label})", got, got_label))

        print(f"  {i:2}. {tag} {q[:55]:55s} → expected={expected} got={got or '—':>5}")

    rate = passed / len(cases) if cases else 0
    print("─" * 80)
    print(f"Pass rate: {passed}/{len(cases)} = {rate:.1%}  (threshold {EVAL_THRESHOLD:.0%})")

    if failed_rows:
        print("\nFailed cases:")
        for q, exp, got, got_label in failed_rows:
            print(f"  • {q}")
            print(f"      expected: {exp}")
            print(f"      got:      {got or '(none)'}  {got_label}")

    return 0 if rate >= EVAL_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
