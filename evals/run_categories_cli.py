"""
Eval kroz Claude Code CLI — paušal preko Pro pretplate, ne plaća se API.

Razlika u odnosu na run_categories.py:
- run_categories.py: koristi Anthropic API (tools= parametar, čita tool_use blok).
- run_categories_cli.py: koristi `claude` CLI komandu, tools schemu šalje kao
  tekst, model vraća JSON odgovor koji se parsira kao tekst.

Test set i threshold isti (category_eval.json).

Pokreni: python evals/run_categories_cli.py
Exit code 0 ako pass-rate >= EVAL_THRESHOLD (default 0.80), inače 1.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.system_prompts import system_prompt  # noqa: E402
from app.tools import ALL_TOOLS, CATEGORIES  # noqa: E402

EVAL_PATH = PROJECT_ROOT / "evals" / "category_eval.json"
EVAL_THRESHOLD = float(os.getenv("EVAL_THRESHOLD", "0.80"))
CLI_MODEL = os.getenv("EVAL_CLI_MODEL", "claude-sonnet-4-6")
CLI_TIMEOUT_S = int(os.getenv("EVAL_CLI_TIMEOUT_S", "300"))


JSON_INSTRUCTION = """
Ti si AI asistent za prodaju (BitLab). Imaš listu alata. Za korisnikov upit,
odluči koji alat bi pozvao i sa kojim argumentima. Odgovori ISKLJUČIVO jednim
JSON objektom, bez ikakvog dodatnog teksta, markdown fence-a, niti komentara.

Format odgovora (striktno):
{"tool": "<naziv_alata>", "input": {<argumenti>}}

Dostupni alati:
"""


def _build_prompt(user_query: str) -> str:
    tools_text = json.dumps(ALL_TOOLS, ensure_ascii=False, indent=2)
    base_sys = system_prompt("chat")
    full = (
        f"{base_sys}\n\n---\n{JSON_INSTRUCTION}\n{tools_text}\n\n"
        f"---\nKorisnikov upit: {user_query}\n\nJSON odgovor:"
    )
    return full


def _strip_fences(text: str) -> str:
    """Skini markdown fence i izvuci prvi balansirani JSON objekat."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text.rsplit("\n", 1)[0] if "\n" in text else text[:-3]
    text = re.sub(r"^(?:json|JSON)\s*[,:]?\s*", "", text.strip())
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        text = text[start : end + 1]
    return text.strip()


def _eval_one(query: str) -> dict:
    """Pozovi claude CLI, parsiraj JSON, vrati tool_name + category_id."""
    prompt = _build_prompt(query)
    try:
        result = subprocess.run(
            ["claude", "--model", CLI_MODEL, "-p", "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"tool_name": None, "category_id": None, "ok_tool": False,
                "error": f"timeout ({CLI_TIMEOUT_S}s)"}

    if result.returncode != 0:
        return {"tool_name": None, "category_id": None, "ok_tool": False,
                "error": f"CLI exit {result.returncode}: {result.stderr.strip()[:200]}"}

    try:
        envelope = json.loads(result.stdout)
        raw_output = envelope.get("result", result.stdout)
    except json.JSONDecodeError:
        raw_output = result.stdout

    cleaned = _strip_fences(raw_output)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return {"tool_name": None, "category_id": None, "ok_tool": False,
                "error": f"JSON parse fail: {exc} | raw: {cleaned[:120]}"}

    tool_name = parsed.get("tool")
    tool_input = parsed.get("input") or {}
    category_id = tool_input.get("category_id") if tool_name == "search_products" else None
    return {
        "tool_name": tool_name,
        "category_id": category_id,
        "ok_tool": tool_name == "search_products",
        "error": None,
    }


def main() -> int:
    if not EVAL_PATH.exists():
        print(f"Nema {EVAL_PATH}", file=sys.stderr)
        return 1

    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))

    passed = 0
    failed_rows: list[tuple[str, str, str | None, str]] = []
    print(f"Eval (CLI): {len(cases)} upita · model={CLI_MODEL} · threshold={EVAL_THRESHOLD:.0%}")
    print("─" * 80)

    for i, case in enumerate(cases, 1):
        q = case["query"]
        expected = case["expected_category_id"]
        r = _eval_one(q)

        if r.get("error"):
            print(f"  {i:2}. ERR  {q[:55]:55s} → {r['error'][:30]}")
            failed_rows.append((q, expected, None, r["error"]))
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
