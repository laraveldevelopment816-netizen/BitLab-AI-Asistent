"""Eval runner — jedna komanda za sve suite-ove.

Pokretanje:
    python -m evals.framework.runner --suite categories
    python -m evals.framework.runner --suite categories --limit 25 --fail-fast
    python -m evals.framework.runner --suite categories --offset 47
    python -m evals.framework.runner --suite categories --resume --limit 25
    python -m evals.framework.runner --suite products --label prompt-v3 --url http://localhost:7778

Exit kod: 0 svi PASS/WARN/NA, 1 bar jedan FAIL, 2 rate limit hit (STOP marker kreiran).
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from pathlib import Path

from . import judge, loader, reporter
from .client import RateLimitError, call_chat
from .types import EvalEntry, EvalVerdict, ToolCall

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_STATE_FILE = _PROJECT_ROOT / "ralph" / "session-state.json"
_STOP_MARKER = _PROJECT_ROOT / "ralph" / "STOP"


def _write_state(suite: str, label: str, offset: int, total: int) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "suite": suite,
        "label": label,
        "offset": offset,
        "total": total,
        "stopped_at": datetime.datetime.now().isoformat(),
        "reason": "rate_limit",
    }
    _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def _read_resume_offset(suite: str) -> int:
    """Vrati offset iz state fajla ako odgovara suite-u i razlog je rate_limit."""
    if not _STATE_FILE.exists():
        return 0
    try:
        state = json.loads(_STATE_FILE.read_text())
        if state.get("suite") == suite and state.get("reason") == "rate_limit":
            return int(state.get("offset", 0))
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return 0


def run_suite(
    suite_path: Path,
    base_url: str,
    label: str,
    limit: int | None,
    offset: int,
    fail_fast: bool,
    run_dir: Path,
) -> int:
    """Pokreni eval suite. Vraća exit kod (0 = OK, 1 = FAIL, 2 = rate limit)."""
    entries = loader.load_suite(suite_path)
    total = len(entries)
    entries = entries[offset:]
    if limit is not None:
        entries = entries[:limit] if limit > 0 else []

    suite_name = suite_path.stem
    verdicts: list[EvalVerdict] = []
    rate_limited = False

    if offset > 0:
        print(f"[eval] Resume: počinjem od entry {offset}/{total} (preskočeno {offset}).")

    for i, entry in enumerate(entries):
        try:
            v = _run_entry(entry, base_url)
        except RateLimitError:
            current_offset = offset + i
            _write_state(suite_name, label, current_offset, total)
            _STOP_MARKER.touch()
            print(
                f"\n[eval] !! Rate limit na entry {entry['id']} "
                f"(index {current_offset}/{total}).\n"
                f"[eval]    State sačuvan -> {_STATE_FILE}\n"
                f"[eval]    STOP marker  -> {_STOP_MARKER}\n"
                f"[eval]    Nastavi poslije reseta sesije:\n"
                f"[eval]      rm ralph/STOP\n"
                f"[eval]      python -m evals.framework.runner "
                f"--suite {suite_name} --resume --limit 25 --label {label}"
            )
            rate_limited = True
            break
        verdicts.append(v)
        if fail_fast and v["overall"] == "FAIL":
            print(f"[eval] --fail-fast: entry {entry['id']} FAIL, stop.")
            break

    if verdicts:
        jsonl_path = reporter.write_jsonl(run_dir, suite_name, label, verdicts)
        html_path = reporter.write_html(run_dir, suite_name, label, verdicts)
        reporter.print_summary(verdicts)
        print(f"[eval] JSONL: {jsonl_path}")
        print(f"[eval] HTML:  {html_path}")

    if rate_limited:
        return 2

    # Uspješan run bez rate limit — obriši state da sljedeći --resume počne od 0.
    if _STATE_FILE.exists():
        _STATE_FILE.unlink()

    failed = sum(1 for v in verdicts if v["overall"] == "FAIL")
    return 1 if failed > 0 else 0


def _run_entry(entry: EvalEntry, base_url: str) -> EvalVerdict:
    t0 = time.time()
    try:
        body = call_chat(base_url, entry["query"], entry.get("history", []))
        tool_calls: list[ToolCall] = body.get("tool_calls", []) or []
        reply = body.get("reply", "") or ""
        iterations = body.get("iterations", 0) or 0
        error: str | None = None
    except RateLimitError:
        raise  # propagate ka run_suite za graceful handling
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
        help="Max N entry-ja po runu. Preporuka: 25 (PWR sesija limit).",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Preskoči prvih N entry-ja (ručni resume).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Čitaj offset iz ralph/session-state.json i nastavi gdje je stalo.",
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

    offset = _read_resume_offset(args.suite) if args.resume else args.offset
    if args.resume and offset > 0:
        print(f"[eval] --resume: nastavljam od index {offset} (iz ralph/session-state.json).")

    run_dir = project_root / "evals" / "runs"
    return run_suite(
        suite_path=suite_path,
        base_url=args.url,
        label=args.label,
        limit=args.limit,
        offset=offset,
        fail_fast=args.fail_fast,
        run_dir=run_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
