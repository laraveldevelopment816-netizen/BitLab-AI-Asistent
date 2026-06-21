"""
Eval runner kroz Claude Code CLI — paušal preko Pro pretplate, ne plaća se API.

Razlika od run.py:
- run.py: HTTP POST /api/chat → BAA server → Anthropic API (plaća se per token)
- run_cli.py: lokalna `claude` komanda + lokalni dispatch alata (Pro paušal)

Test set isti (test_questions.json). Provjeri: expect_tool, expect_contains,
expect_not_contains — identičan kriterijum kao u run.py.

Multi-turn agent loop:
  1. Claude vrati ili {"tool":...,"input":...} ili {"reply":...}
  2. Ako tool — Python ga izvrši lokalno (dispatch) i šalje rezultat nazad
  3. Ako reply — finalni odgovor, kraj loopa

Pokreni:
    .venv/bin/python evals/run_cli.py
    .venv/bin/python evals/run_cli.py --channel email
    .venv/bin/python evals/run_cli.py --verbose
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.system_prompts import system_prompt  # noqa: E402
from app.tools import ALL_TOOLS, dispatch  # noqa: E402

QUESTIONS_FILE = PROJECT_ROOT / "evals" / "test_questions.json"
DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_TIMEOUT_S = 300
MAX_ITERATIONS = 5

JSON_INSTRUCTION = """\
Format odgovora — striktno jedan JSON objekat po turnu, bez markdown fence-a:

- Za poziv alata: {"tool": "<naziv>", "input": {<args>}}
- Za finalni odgovor korisniku: {"reply": "<tekst>"}

Nikada oba u istom turnu. Nikada čist tekst van JSON-a.
"""


def _build_prompt(channel: str, user_query: str, turns: list[tuple[str, dict, str]]) -> str:
    """Sastavi puni prompt: system + alati + format + konverzacija dosad."""
    tools_text = json.dumps(ALL_TOOLS, ensure_ascii=False, indent=2)
    base = system_prompt(channel)

    history_lines: list[str] = []
    for t_name, t_input, t_result in turns:
        history_lines.append(
            f'Asistent: {{"tool":"{t_name}","input":{json.dumps(t_input, ensure_ascii=False)}}}'
        )
        history_lines.append(f"Tool rezultat: {t_result}")
    history_text = "\n".join(history_lines) if history_lines else "(nema prethodnih alata)"

    return (
        f"{base}\n\n"
        f"---\n## Alati\n{tools_text}\n\n"
        f"## Format\n{JSON_INSTRUCTION}\n\n"
        f"## Korisnikov upit\n{user_query}\n\n"
        f"## Prethodni alati (po redu)\n{history_text}\n\n"
        f"## Sljedeći JSON odgovor:"
    )


def _strip_fences(text: str) -> str:
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


def _call_claude_cli(prompt: str, model: str, timeout: int) -> tuple[str, str]:
    """Vrati (raw_output, error). Error je prazan na uspjeh."""
    try:
        result = subprocess.run(
            ["claude", "--model", model, "-p", "--output-format", "json"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "", f"timeout ({timeout}s)"

    if result.returncode != 0:
        return "", f"CLI exit {result.returncode}: {result.stderr.strip()[:200]}"

    try:
        envelope = json.loads(result.stdout)
        return envelope.get("result", result.stdout), ""
    except json.JSONDecodeError:
        return result.stdout, ""


def _run_agent(channel: str, question: str, model: str, timeout: int) -> dict:
    """Multi-turn loop. Vrati: {reply, tools_used, iterations, error}."""
    turns: list[tuple[str, dict, str]] = []
    tools_used: list[str] = []

    for i in range(1, MAX_ITERATIONS + 1):
        prompt = _build_prompt(channel, question, turns)
        raw, err = _call_claude_cli(prompt, model, timeout)
        if err:
            return {"reply": "", "tools_used": tools_used, "iterations": i, "error": err}

        cleaned = _strip_fences(raw)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            return {
                "reply": "",
                "tools_used": tools_used,
                "iterations": i,
                "error": f"JSON parse: {exc} | raw: {cleaned[:120]}",
            }

        if "reply" in parsed and isinstance(parsed["reply"], str):
            return {
                "reply": parsed["reply"],
                "tools_used": tools_used,
                "iterations": i,
                "error": None,
            }

        if "tool" in parsed:
            name = parsed["tool"]
            t_input = parsed.get("input") or {}
            tools_used.append(name)
            try:
                result = dispatch(name, t_input)
            except Exception as exc:  # pragma: no cover — safety net
                result = f"Tool error: {exc}"
            turns.append((name, t_input, result))
            continue

        return {
            "reply": "",
            "tools_used": tools_used,
            "iterations": i,
            "error": f"unexpected JSON shape: {cleaned[:120]}",
        }

    return {
        "reply": "",
        "tools_used": tools_used,
        "iterations": MAX_ITERATIONS,
        "error": f"max iterations ({MAX_ITERATIONS}) reached bez reply-ja",
    }


def _check(result: dict, q: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []
    tools_used = result.get("tools_used", [])
    reply_lower = (result.get("reply") or "").lower()

    expect_tool = q.get("expect_tool")
    if expect_tool is not None:
        if expect_tool not in tools_used:
            failures.append(f"expect_tool={expect_tool!r} nije pozvan (korišteni: {tools_used})")
    else:
        if tools_used:
            failures.append(f"očekivano 0 alata, korišten: {tools_used}")

    for expected in q.get("expect_contains", []):
        if expected.lower() not in reply_lower:
            failures.append(f"reply ne sadrži '{expected}'")

    for forbidden in q.get("expect_not_contains", []):
        if forbidden.lower() in reply_lower:
            failures.append(f"reply SADRŽI zabranjeno '{forbidden}'")

    return len(failures) == 0, failures


def _truncate(text: str, n: int = 80) -> str:
    text = text.replace("\n", " ")
    return text[:n] + "…" if len(text) > n else text


def run(channel_filter: str | None, verbose: bool, model: str, timeout: int) -> int:
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    if channel_filter:
        questions = [q for q in questions if q.get("channel", "chat") == channel_filter]
    if not questions:
        print(f"Nema pitanja za kanal '{channel_filter}'.")
        return 0

    print(f"\nBitLab eval (CLI) → model={model}, timeout={timeout}s")
    print(f"Pitanja: {len(questions)}")
    print("─" * 100)

    col_q, col_t = 44, 22
    print(f"{'#':<4} {'Pitanje':<{col_q}} {'Alati':<{col_t}} {'Res':>5} {'iter':>5} {'sec':>6}")
    print("─" * 100)

    passed = failed = skipped = 0
    for q in questions:
        qid = q["id"]
        question = q["q"]
        channel = q.get("channel", "chat")

        t0 = time.perf_counter()
        try:
            result = _run_agent(channel, question, model, timeout)
        except KeyboardInterrupt:
            print("\nPrekinuto.")
            break
        latency = time.perf_counter() - t0

        if result.get("error"):
            err_short = _truncate(result["error"], col_t)
            q_short = _truncate(f"[{channel}] {question}", col_q)
            print(f"{qid:<4} {q_short:<{col_q}} {err_short:<{col_t}} {'ERR':>5} "
                  f"{result.get('iterations', 0):>5} {int(latency):>6}")
            skipped += 1
            continue

        ok, failures = _check(result, q)
        tools_str = ",".join(result.get("tools_used", []) or ["—"])
        res_str = "✓" if ok else "✗"
        iters = result.get("iterations", 0)

        q_short = _truncate(f"[{channel}] {question}", col_q)
        print(f"{qid:<4} {q_short:<{col_q}} {tools_str:<{col_t}} {res_str:>5} "
              f"{iters:>5} {int(latency):>6}")

        if not ok:
            for reason in failures:
                print(f"       ↳ {reason}")
        if verbose:
            print(f"       Reply: {_truncate(result.get('reply', ''), 120)}")

        if ok:
            passed += 1
        else:
            failed += 1

    print("─" * 100)
    total = passed + failed + skipped
    print(f"Rezultat: {passed}/{total} prošlo  ({failed} palo, {skipped} greška)\n")
    return 0 if failed == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="BitLab eval kroz Claude Code CLI")
    parser.add_argument("--channel", default=None, help="Filter: chat | voice | email")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model za CLI")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S, help="Timeout (s) po pozivu")
    parser.add_argument("--verbose", action="store_true", help="Ispiši odgovore")
    args = parser.parse_args()
    sys.exit(run(args.channel, args.verbose, args.model, args.timeout))


if __name__ == "__main__":
    main()
