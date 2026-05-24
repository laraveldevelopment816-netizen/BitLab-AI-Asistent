"""Eval runner — jedna komanda za sve suite-ove sa cache + sample + resume.

Pokretanje:
    python -m evals.framework.runner --suite categories
    python -m evals.framework.runner --suite categories --mode sample --label baseline
    python -m evals.framework.runner --suite categories --resume baseline   # nastavi od checkpoint-a
    python -m evals.framework.runner --suite categories --no-cache
    python -m evals.framework.runner --suite categories --cache-stats

Exit kodovi:
    0 — sve PASS/WARN/NA.
    1 — bar jedan FAIL.
    2 — suite fajl ne postoji.
    3 — rate limit, snimljen checkpoint, resume-uj kasnije.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import budget, cache, client, errors, judge, loader, reporter, sampler
from .types import EvalEntry, EvalVerdict, ToolCall


def _get_signature() -> tuple[str, str]:
    """Vrati (system_prompt, tools_signature) iz app/ paketa za cache hash."""
    try:
        from app.agent import SYSTEM_PROMPT_V1
        from app.tools import ALL_TOOLS_ANTHROPIC

        return SYSTEM_PROMPT_V1, json.dumps(ALL_TOOLS_ANTHROPIC, sort_keys=True, ensure_ascii=False)
    except ImportError:
        return "", ""


def _checkpoint_path(run_dir: Path, suite_name: str, label: str) -> Path:
    return run_dir / f"{suite_name}-{label}.checkpoint.json"


def _read_checkpoint(path: Path) -> int:
    """Vrati next_index iz checkpoint-a; 0 ako fajl ne postoji ili je malformed."""
    if not path.exists():
        return 0
    try:
        cp = json.loads(path.read_text(encoding="utf-8"))
        return int(cp.get("next_index", 0))
    except (json.JSONDecodeError, OSError, ValueError):
        return 0


def _write_checkpoint(path: Path, next_index: int, label: str, reason: str) -> None:
    """Snima checkpoint sa next_index — entry koji treba ponoviti pri resume-u."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"next_index": next_index, "label": label, "reason": reason},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _default_budget_dir() -> Path:
    """Per-user state (van repoa) — `~/.cache/bitlab-ralph/`."""
    return Path.home() / ".cache" / "bitlab-ralph"


def _default_pause_file() -> Path:
    """Default `<project_root>/ralph/PAUSE` — runner piše ovdje, ralph.sh čita."""
    return Path(__file__).resolve().parent.parent.parent / "ralph" / "PAUSE"


def _estimate_reset_epoch(budget_dir: Path) -> int:
    """Procjena reset epoch — najstariji unos u pwr_calls.jsonl + 5h, fallback now+5h."""
    log = budget_dir / "pwr_calls.jsonl"
    now = time.time()
    if not log.exists():
        return int(now + budget.WINDOW_SECONDS)
    oldest: float | None = None
    with log.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ts = float(json.loads(line).get("ts", 0))
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
            if oldest is None or ts < oldest:
                oldest = ts
    if oldest is None:
        return int(now + budget.WINDOW_SECONDS)
    return int(oldest + budget.WINDOW_SECONDS)


def _write_pause_marker(pause_file: Path, until_epoch: int, reason: str) -> None:
    """Snima PAUSE marker sa `until=<epoch>` u prvi red — ralph.sh ga detektuje."""
    pause_file.parent.mkdir(parents=True, exist_ok=True)
    pause_file.write_text(
        f"until={until_epoch}\nreason={reason}\n",
        encoding="utf-8",
    )


def _fmt_epoch_local(epoch: int | float) -> str:
    """Konvertuje epoch u lokalni human-readable format (BS/SR/CG: dd.mm.yyyy HH:MM:SS).

    Koristi se za sve stdout poruke ka korisniku — fajl sadržaj `until=<epoch>`
    ostaje program-readable (parsing u `wait_pause.py`).
    """
    import datetime

    return datetime.datetime.fromtimestamp(epoch).strftime("%d.%m.%Y %H:%M:%S")


def run_suite(
    suite_path: Path,
    base_url: str,
    label: str,
    limit: int | None,
    fail_fast: bool,
    run_dir: Path,
    cache_dir: Path,
    use_cache: bool,
    mode: str,
    resume_label: str | None = None,
    budget_dir: Path | None = None,
    max_calls: int = budget.DEFAULT_MAX_CALLS,
    pause_file: Path | None = None,
) -> int:
    """Pokreni eval suite. Vraća exit kod (0 OK, 1 FAIL, 3 rate-limit ili budget exhausted)."""
    entries = loader.load_suite(suite_path)

    if mode == "sample":
        entries = sampler.stratified_sample(entries, target_size=30, seed=42)
        print(f"[eval] sample mode: {len(entries)} entries (stratified, seed=42)")
    if limit is not None:
        entries = entries[:limit] if limit > 0 else []

    suite_name = suite_path.stem
    checkpoint_file = _checkpoint_path(run_dir, suite_name, label)
    if budget_dir is None:
        budget_dir = _default_budget_dir()
    # pause_file=None znači testovi ne care o PAUSE marker pisanju (skip).
    # CLI main() prosljeđuje project_root/ralph/PAUSE eksplicitno.

    # Resume: čitaj checkpoint ako resume_label dat.
    start_index = 0
    if resume_label is not None:
        resume_checkpoint = _checkpoint_path(run_dir, suite_name, resume_label)
        start_index = _read_checkpoint(resume_checkpoint)
        if start_index > 0:
            print(f"[resume] krećem od index {start_index} (checkpoint {resume_checkpoint})")

    system_prompt, tools_sig = _get_signature() if use_cache else ("", "")
    cache_enabled = use_cache and system_prompt != ""

    # Fix #1: Resume učitava postojeće verdicte iz stable JSONL — Faza 1 acceptance
    # metric čita JEDAN fajl sa svim verdicts kroz sve resume cikluse.
    verdicts: list[EvalVerdict] = []
    if resume_label is not None and start_index > 0:
        verdicts = reporter.read_existing_verdicts(run_dir, suite_name, resume_label)
        if verdicts:
            print(f"[resume] učitano {len(verdicts)} prethodnih verdicata iz stable JSONL")
    cache_hits = 0
    paused = False

    for i in range(start_index, len(entries)):
        entry = entries[i]

        v: EvalVerdict | None = None
        if cache_enabled:
            hash_key = cache.compute_hash(entry, system_prompt, tools_sig)
            cached = cache.cache_get(cache_dir, hash_key)
            if cached is not None:
                v = cached
                cache_hits += 1
                print(f"[cache HIT] {entry['id']} → {v['overall']}")

        if v is None:
            # Budget gate — prije skupog PWR poziva, provjeri 5h prozor.
            if budget.should_pause(budget_dir, max_calls=max_calls):
                count = budget.count_calls_last_5h(budget_dir)
                reason = (
                    f"budget exhausted: {count} poziva u 5h ≥ "
                    f"{int(max_calls * budget.DEFAULT_THRESHOLD)} (max_calls={max_calls})"
                )
                _write_checkpoint(checkpoint_file, i, label, reason)
                if pause_file is not None:
                    until = _estimate_reset_epoch(budget_dir)
                    _write_pause_marker(pause_file, until, reason)
                    print(
                        f"[budget] paused na index {i} → checkpoint {checkpoint_file}, "
                        f"PAUSE marker {pause_file} (aktivan do {_fmt_epoch_local(until)})"
                    )
                else:
                    print(f"[budget] paused na index {i} → checkpoint {checkpoint_file}")
                paused = True
                break

            try:
                v = _run_entry(entry, base_url)
            except errors.RateLimitDetected as e:
                _write_checkpoint(checkpoint_file, i, label, f"rate_limit: {e}")
                if pause_file is not None:
                    until = _estimate_reset_epoch(budget_dir)
                    _write_pause_marker(pause_file, until, f"rate_limit: {e}")
                    print(
                        f"[rate-limit] checkpoint {checkpoint_file}, "
                        f"PAUSE marker {pause_file} (aktivan do {_fmt_epoch_local(until)})"
                    )
                else:
                    print(f"[rate-limit] checkpoint {checkpoint_file}")
                paused = True
                break

            budget.record_call(budget_dir)
            if cache_enabled and v["error"] is None:
                hash_key = cache.compute_hash(entry, system_prompt, tools_sig)
                cache.cache_put(cache_dir, hash_key, v)

        verdicts.append(v)
        # Fix #1: append per-entry u stable <suite>-<label>.jsonl
        # (resume nastavlja u isti fajl umjesto da pravi novi TS-ovan).
        reporter.append_verdict(run_dir, suite_name, label, v)
        if fail_fast and v["overall"] == "FAIL":
            print(f"[eval] --fail-fast: entry {entry['id']} FAIL, stop.")
            break

    jsonl_path = reporter._stable_jsonl_path(run_dir, suite_name, label)
    html_path = reporter.write_html(run_dir, suite_name, label, verdicts)
    reporter.print_summary(verdicts)
    if cache_enabled:
        print(
            f"[cache] hits={cache_hits} / {len(verdicts)} "
            f"({cache_hits / max(len(verdicts), 1) * 100:.1f}%)"
        )
    print(f"[eval] JSONL: {jsonl_path}")
    print(f"[eval] HTML:  {html_path}")

    if paused:
        return 3

    # Clean completion — ukloni checkpoint ako postoji (od prethodnog rate-limit-a).
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        print(f"[cleanup] obrisan stari checkpoint {checkpoint_file}")

    failed = sum(1 for v in verdicts if v["overall"] == "FAIL")
    return 1 if failed > 0 else 0


def _run_entry(entry: EvalEntry, base_url: str) -> EvalVerdict:
    """Pokreni jedan entry. Propagira RateLimitDetected gore (runner snima checkpoint)."""
    t0 = time.time()
    try:
        body = client.call_chat(base_url, entry["query"], entry.get("history", []))
        tool_calls: list[ToolCall] = body.get("tool_calls", []) or []
        reply = body.get("reply", "") or ""
        iterations = body.get("iterations", 0) or 0
        error: str | None = None
    except errors.RateLimitDetected:
        raise  # runner hvata
    except Exception as e:  # noqa: BLE001 — eval mora preživjeti druge greške
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
    parser = argparse.ArgumentParser(description="Eval suite runner za bitlab-ai-asistent")
    parser.add_argument("--suite", required=True, help="Naziv suite-a (npr. 'categories')")
    parser.add_argument(
        "--mode",
        choices=["sample", "full"],
        default="sample",
        help="sample = stratificirano 30 entry-ja (default, brzi signal za iter); full = svih 250.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Pokreni samo prvih N entry-ja (0 = nijedan, smoke).",
    )
    parser.add_argument("--label", default="adhoc", help="Label u output fajlu.")
    parser.add_argument("--fail-fast", action="store_true", help="Stani na prvom FAIL-u.")
    parser.add_argument(
        "--url",
        default="http://localhost:7778",
        help="Base URL FastAPI servera (default http://localhost:7778).",
    )
    parser.add_argument("--no-cache", action="store_true", help="Bypass verdict cache.")
    parser.add_argument(
        "--cache-stats", action="store_true", help="Ispiši samo statistiku cache-a i exit."
    )
    parser.add_argument(
        "--resume",
        default=None,
        help="Resume label — čita <suite>-<resume>.checkpoint.json i kreće od next_index.",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=budget.DEFAULT_MAX_CALLS,
        help=f"MAX_CALLS u 5h sliding window (default {budget.DEFAULT_MAX_CALLS}, pause na {int(budget.DEFAULT_MAX_CALLS * budget.DEFAULT_THRESHOLD)}).",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    cache_dir = project_root / "evals" / "cache"

    if args.cache_stats:
        stats = cache.cache_stats(cache_dir)
        print(f"[cache] {cache_dir}")
        print(
            f"  total={stats['total']} pass={stats['pass']} "
            f"fail={stats['fail']} warn={stats['warn']}"
        )
        return 0

    suite_path = project_root / "evals" / "sets" / f"{args.suite}.jsonl"
    if not suite_path.exists():
        print(f"FATAL: suite fajl ne postoji: {suite_path}")
        return 2

    run_dir = project_root / "evals" / "runs"
    pause_file = project_root / "ralph" / "PAUSE"
    return run_suite(
        suite_path=suite_path,
        base_url=args.url,
        label=args.label,
        limit=args.limit,
        fail_fast=args.fail_fast,
        run_dir=run_dir,
        cache_dir=cache_dir,
        use_cache=not args.no_cache,
        mode=args.mode,
        resume_label=args.resume,
        max_calls=args.max_calls,
        pause_file=pause_file,
    )


if __name__ == "__main__":
    sys.exit(main())
