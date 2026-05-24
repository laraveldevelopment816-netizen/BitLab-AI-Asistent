"""Eval runner — jedna komanda za sve suite-ove sa verdict cache i sample mode.

Pokretanje:
    python -m evals.framework.runner --suite categories
    python -m evals.framework.runner --suite categories --mode sample --label baseline
    python -m evals.framework.runner --suite categories --limit 5 --fail-fast
    python -m evals.framework.runner --suite categories --no-cache  # bypass cache
    python -m evals.framework.runner --suite categories --cache-stats  # dry, samo statistika

Exit kod: 0 ako svi entry-ji PASS/WARN/NA, 1 ako bar jedan FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import cache, client, judge, loader, reporter, sampler
from .types import EvalEntry, EvalVerdict, ToolCall


def _get_signature() -> tuple[str, str]:
    """Vrati (system_prompt, tools_signature) iz app/ paketa.

    Tools signature: stable JSON string ALL_TOOLS_ANTHROPIC. Ako se shape
    promijeni, hash se mijenja → cache invalidira.
    """
    try:
        from app.agent import SYSTEM_PROMPT_V1
        from app.tools import ALL_TOOLS_ANTHROPIC

        return SYSTEM_PROMPT_V1, json.dumps(ALL_TOOLS_ANTHROPIC, sort_keys=True, ensure_ascii=False)
    except ImportError:
        # Defensive: ako app/ nije importable (npr. CI bez deps), cache disable.
        return "", ""


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
) -> int:
    """Pokreni eval suite. Vraća exit kod (0 = OK, 1 = bar jedan FAIL)."""
    entries = loader.load_suite(suite_path)

    if mode == "sample":
        entries = sampler.stratified_sample(entries, target_size=30, seed=42)
        print(f"[eval] sample mode: {len(entries)} entries (stratified, seed=42)")
    if limit is not None:
        entries = entries[:limit] if limit > 0 else []

    system_prompt, tools_sig = _get_signature() if use_cache else ("", "")
    cache_enabled = use_cache and system_prompt != ""

    verdicts: list[EvalVerdict] = []
    cache_hits = 0
    for entry in entries:
        v: EvalVerdict | None = None
        if cache_enabled:
            hash_key = cache.compute_hash(entry, system_prompt, tools_sig)
            cached = cache.cache_get(cache_dir, hash_key)
            if cached is not None:
                v = cached
                cache_hits += 1
                print(f"[cache HIT] {entry['id']} → {v['overall']}")

        if v is None:
            v = _run_entry(entry, base_url)
            if cache_enabled and v["error"] is None:
                hash_key = cache.compute_hash(entry, system_prompt, tools_sig)
                cache.cache_put(cache_dir, hash_key, v)

        verdicts.append(v)
        if fail_fast and v["overall"] == "FAIL":
            print(f"[eval] --fail-fast: entry {entry['id']} FAIL, stop.")
            break

    suite_name = suite_path.stem
    jsonl_path = reporter.write_jsonl(run_dir, suite_name, label, verdicts)
    html_path = reporter.write_html(run_dir, suite_name, label, verdicts)
    reporter.print_summary(verdicts)
    if cache_enabled:
        print(
            f"[cache] hits={cache_hits} / {len(verdicts)} ({cache_hits / max(len(verdicts), 1) * 100:.1f}%)"
        )
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
    parser = argparse.ArgumentParser(description="Eval suite runner za bitlab-ai-asistent")
    parser.add_argument("--suite", required=True, help="Naziv suite-a (npr. 'categories')")
    parser.add_argument(
        "--mode",
        choices=["sample", "full"],
        default="full",
        help="sample = stratificirano 30 entry-ja (brzi signal); full = sve.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Pokreni samo prvih N entry-ja (0 = nijedan, smoke test runner-a).",
    )
    parser.add_argument("--label", default="adhoc", help="Label u output fajlu.")
    parser.add_argument("--fail-fast", action="store_true", help="Stani na prvom FAIL-u.")
    parser.add_argument(
        "--url",
        default="http://localhost:7778",
        help="Base URL FastAPI servera (default http://localhost:7778).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass verdict cache (uvijek zove backend).",
    )
    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="Ispiši samo statistiku cache-a i exit.",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    cache_dir = project_root / "evals" / "cache"

    if args.cache_stats:
        stats = cache.cache_stats(cache_dir)
        print(f"[cache] {cache_dir}")
        print(
            f"  total={stats['total']} pass={stats['pass']} fail={stats['fail']} warn={stats['warn']}"
        )
        return 0

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
        cache_dir=cache_dir,
        use_cache=not args.no_cache,
        mode=args.mode,
    )


if __name__ == "__main__":
    sys.exit(main())
