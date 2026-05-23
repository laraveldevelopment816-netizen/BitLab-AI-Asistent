"""Reporter — JSONL i HTML output, plus terminal summary za Ralph/CI."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .types import EvalVerdict


def write_jsonl(run_dir: Path, suite: str, label: str, verdicts: list[EvalVerdict]) -> Path:
    """Write JSONL run file. Vraća putanju."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / f"{suite}-{label}-{ts}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for v in verdicts:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")
    return out


def write_html(run_dir: Path, suite: str, label: str, verdicts: list[EvalVerdict]) -> Path:
    """Minimalni HTML dashboard sa summary i per-entry tabelom."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / f"{suite}-{label}-{ts}.html"
    total = len(verdicts)
    passed = sum(1 for v in verdicts if v["overall"] == "PASS")
    failed = sum(1 for v in verdicts if v["overall"] == "FAIL")
    warned = sum(1 for v in verdicts if v["overall"] == "WARN")
    pass_rate = (passed / total * 100) if total else 0.0

    rows = "\n".join(_html_row(v) for v in verdicts)
    html = f"""<!DOCTYPE html>
<html lang="bs"><head><meta charset="utf-8"><title>{suite} — {label}</title>
<style>
body {{ font: 14px/1.4 -apple-system, sans-serif; max-width: 1200px; margin: 2em auto; padding: 0 1em; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; vertical-align: top; }}
tr.pass {{ background: #e8f5e9; }}
tr.fail {{ background: #ffebee; }}
tr.warn {{ background: #fff8e1; }}
tr.na {{ background: #f5f5f5; }}
.summary {{ font-size: 1.2em; margin-bottom: 1em; padding: 0.5em; background: #f0f4ff; border-radius: 4px; }}
code {{ background: #fafafa; padding: 1px 4px; border-radius: 3px; font-size: 12px; }}
</style></head><body>
<h1>{suite} — {label} ({ts})</h1>
<p class="summary">Total: {total} | PASS: {passed} | FAIL: {failed} | WARN: {warned} | Pass rate: {pass_rate:.1f}%</p>
<table>
<thead><tr><th>ID</th><th>Routing</th><th>Result</th><th>Overall</th><th>Time</th><th>Tool calls</th><th>Error / Reply</th></tr></thead>
<tbody>
{rows}
</tbody></table></body></html>"""
    out.write_text(html, encoding="utf-8")
    return out


def _html_row(v: EvalVerdict) -> str:
    css_class = v["overall"].lower()
    tool_calls_str = ", ".join(c["name"] for c in v["actual_tool_calls"]) or "—"
    error_or_reply = v.get("error") or (v.get("reply") or "")[:120]
    return (
        f"<tr class='{css_class}'>"
        f"<td>{_escape(v['entry_id'])}</td>"
        f"<td>{v['routing']}</td>"
        f"<td>{v['result']}</td>"
        f"<td><b>{v['overall']}</b></td>"
        f"<td>{v['elapsed_ms']}ms</td>"
        f"<td><code>{_escape(tool_calls_str)}</code></td>"
        f"<td><code>{_escape(error_or_reply)}</code></td>"
        f"</tr>"
    )


def _escape(s: str) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def print_summary(verdicts: list[EvalVerdict]) -> None:
    """Terminal summary — kratko, za Ralph i CI log."""
    total = len(verdicts)
    if total == 0:
        print("[eval] no entries — exit 0")
        return
    passed = sum(1 for v in verdicts if v["overall"] == "PASS")
    failed = sum(1 for v in verdicts if v["overall"] == "FAIL")
    warned = sum(1 for v in verdicts if v["overall"] == "WARN")
    pass_rate = passed / total * 100
    print(
        f"[eval] {total} entries | PASS {passed} | FAIL {failed} | WARN {warned} | "
        f"rate {pass_rate:.1f}%"
    )
    for v in verdicts:
        if v["overall"] == "FAIL":
            err = (v.get("error") or "")[:80]
            print(f"  FAIL  {v['entry_id']}  routing={v['routing']} result={v['result']}  {err}")
