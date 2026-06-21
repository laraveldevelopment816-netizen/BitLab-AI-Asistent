"""Generiše dev eval suite (`evals/sets/categories_dev.jsonl`) — mali HARD uzorak
za brzi/jeftin gate dok se podešava prompt (kartica dsmp).

Sastav:
  1. REGRESIJE: entry-ji koji su u iter8 baseline-u bili PASS a u iter17-final FAIL
     (tool-apstinencija iz EVAL_REGRESIJA_iter17.md). Izvučeni poređenjem polja
     `overall` u dva run fajla, pa povučeni VERBATIM iz canonical `categories.jsonl`.
  2. NEGATIVCI: kontrolni "ne smije zvati tool" slučajevi iz `categories_manual.jsonl`
     (da forsiranje toola ne pretjera u drugom smjeru) — po par iz svakog subtype-a.

Canonical setovi se NE diraju (eval-set invariant) — ovaj skript samo SELEKTUJE.
Regeneriši sa:  .venv/bin/python -m scripts.gen_dev_sample
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "evals" / "runs"
SETS = ROOT / "evals" / "sets"

BASELINE_RUN = RUNS / "categories-ralph-iter8-pattern-analysis.jsonl"
REGRESSED_RUN = RUNS / "categories-ralph-iter17-prompt-fix-final.jsonl"
CANONICAL = SETS / "categories.jsonl"
MANUAL = SETS / "categories_manual.jsonl"
OUT = SETS / "categories_dev.jsonl"

# Negativci iz manual seta: koliko po subtype-u (not_in_catalog / ambiguous_name /
# typo_likely / out_of_scope) — kontrola da forsiranje toola ne pretjera.
NEGATIVES_PER_SUBTYPE = 2


def _read_jsonl(path: Path) -> list[dict]:
    """JSONL u listu dict-ova; preskoči // komentare i prazne linije."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("//"):
            rows.append(json.loads(s))
    return rows


def _verdicts(path: Path) -> dict[str, str]:
    """{entry_id: overall (PASS/FAIL)} iz run fajla."""
    return {r["entry_id"]: r["overall"] for r in _read_jsonl(path)}


def _raw_lines_by_id(path: Path) -> dict[str, str]:
    """{id: sirova JSONL linija} — entry se povlači verbatim, bez re-serializacije."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("//"):
            out[json.loads(s)["id"]] = s
    return out


def main() -> int:
    base = _verdicts(BASELINE_RUN)
    regr = _verdicts(REGRESSED_RUN)
    common = base.keys() & regr.keys()
    regressions = sorted(e for e in common if base[e] == "PASS" and regr[e] == "FAIL")

    canonical = _raw_lines_by_id(CANONICAL)
    missing = [e for e in regressions if e not in canonical]
    positives = [canonical[e] for e in regressions if e in canonical]

    # Negativci: po NEGATIVES_PER_SUBTYPE iz svakog subtype-a (zadnji tag).
    by_subtype: dict[str, list[dict]] = {}
    for e in _read_jsonl(MANUAL):
        sub = e["tags"][-1] if e.get("tags") else "neg"
        by_subtype.setdefault(sub, []).append(e)
    negatives = [
        json.dumps(e, ensure_ascii=False)
        for sub in sorted(by_subtype)
        for e in by_subtype[sub][:NEGATIVES_PER_SUBTYPE]
    ]

    header = (
        "// Auto-generisano iz scripts/gen_dev_sample.py — ne edituj rukom.\n"
        f"// HARD dev-uzorak: {len(positives)} regresija (iter8 PASS -> iter17 FAIL) "
        f"+ {len(negatives)} negativaca.\n"
        "// Regeneriši: .venv/bin/python -m scripts.gen_dev_sample\n"
    )
    OUT.write_text(header + "\n".join(positives + negatives) + "\n", encoding="utf-8")

    print(f"[gen_dev_sample] zajednickih entry-ja: {len(common)}")
    print(f"[gen_dev_sample] regresija (PASS->FAIL): {len(regressions)}")
    if missing:
        print(f"[gen_dev_sample] UPOZORENJE: {len(missing)} regresija nije u canonical: {missing}")
    print(f"[gen_dev_sample] negativaca: {len(negatives)}")
    print(f"[gen_dev_sample] ukupno u {OUT.name}: {len(positives) + len(negatives)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
