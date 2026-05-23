"""Eval runner — jedna komanda za sve suite-ove.

Pokretanje:
    python -m evals.framework.runner --suite categories
    python -m evals.framework.runner --suite categories --limit 5 --fail-fast
    python -m evals.framework.runner --suite products --label prompt-v3 --url http://localhost:7778

Exit kod: 0 ako svi entry-ji PASS/WARN/NA, 1 ako bar jedan FAIL.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import client, judge, loader, reporter
from .types import EvalEntry, EvalVerdict, ToolCall


def run_suite(
    suite_path: Path,
    base_url: str,
    label: str,
    limit: int | None,
    fail_fast: bool,
    run_dir: Path,
) -> int:
    """Pokreni eval suite. Vraća exit kod (0 = OK, 1 = bar jedan FAIL)."""
    entries = loader.load_suite(suite_path)
    if limit is not None:
        entries = entries[:limit] if limit > 0 else []

    verdicts: list[EvalVerdict] = []
    for entry in entries:
        v = _run_entry(entry, base_url)
        verdicts.append(v)
        if fail_fast and v["overall"] == "FAIL":
            print(f"[eval] --fail-fast: entry {entry['id']} FAIL, stop.")
            break

    suite_name = suite_path.stem
    jsonl_path = reporter.write_jsonl(run_dir, suite_name, label, verdicts)
    html_path = reporter.write_html(run_dir, suite_name, label, verdicts)
    reporter.print_summary(verdicts)
    print(f"[eval] JSONL: {jsonl_path}")
    print(f"[eval] HTML:  {html_path}")

    failed = sum(1 for v in verdicts if v["overall"] == "FAIL")
    return 1 if failed > 0 else 0


def _run_entry(entry: EvalEntry, base_url: str) -> EvalVerdict:
    t0 = time.time()
    try:
        body = client.call_chat(base_url, entry["query"], entry.get("history", []))
        tool_calls: list[ToolCall] = body.get("tool_calls", []) or []
        reply = body.get("reply", "") or ""
        iterations = body.get("iterations", 0) or 0
        error: str | None = None
    except Exception as e:  # noqa: BLE001 — eval mora preživjeti bilo koji error
        tool_calls = []
        reply = ""
        iterations = 0
        error = f"{type(e).__name__}: {e}"

    elapsed_ms = int((time.time() - t0) * 1000)

    if error is not None:
        return {
            "entry_id": entry["id"],
            "routing": "FAIL",
            "result": "FAIL",
            "overall": "FAIL",
            "actual_tool_calls": [],
            "reply": "",
            "iterations": 0,
            "error": error,
            "elapsed_ms": elapsed_ms,
        }

    routing = judge.verdict_routing(entry, tool_calls)
    result = judge.verdict_result(entry, tool_calls, reply)
    overall = judge.verdict_overall(routing, result)

    return {
        "entry_id": entry["id"],
        "routing": routing,
        "result": result,
        "overall": overall,
        "actual_tool_calls": tool_calls,
        "reply": reply,
        "iterations": iterations,
        "error": None,
        "elapsed_ms": elapsed_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Eval suite runner za bitlab-ai-asistent",
    )
    parser.add_argument(
        "--suite",
        required=True,
        help="Naziv suite-a (npr. 'categories') — čita evals/sets/<suite>.jsonl",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Pokreni samo prvih N entry-ja (0 = nijedan, smoke test runner-a).",
    )
    parser.add_argument(
        "--label",
        default="adhoc",
        help="Label u output fajlu (npr. 'baseline', 'prompt-v2').",
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stani na prvom FAIL-u.")
    parser.add_argument(
        "--url",
        default="http://localhost:7778",
        help="Base URL FastAPI servera (default http://localhost:7778).",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    suite_path = project_root / "evals" / "sets" / f"{args.suite}.jsonl"
    if not suite_path.exists():
        print(f"FATAL: suite fajl ne postoji: {suite_path}")
        return 2

    run_dir = project_root / "evals" / "runs"
    return run_suite(
        suite_path=suite_path,
        base_url=args.url,
        label=args.label,
        limit=args.limit,
        fail_fast=args.fail_fast,
        run_dir=run_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
