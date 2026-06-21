"""Generiše hard eval suite (`evals/sets/categories_acpt_fails.jsonl`) — padovi
iz zadnjeg PUNOG acceptance runa (kartice tght/acpt). Jeftin gate za podešavanje
enum + temperature na trenutnim padajućim slučajevima PRIJE punog re-runa od 250.

Sastav:
  1. PADOVI: entry-ji sa `overall == FAIL` iz acceptance run fajla
     (`categories-acpt-full.jsonl`), povučeni VERBATIM iz canonical
     `categories.jsonl`.
  2. NEGATIVCI: isti kontrolni "ne smije zvati tool" slučajevi kao u
     `gen_dev_sample` — da stezanje (enum/temp) ne pretjera u drugom smjeru.

Napomena: acceptance run je OD PRIJE leaf-priority fixa (d16b8ab). Pa puštanje
ovog seta na trenutni kod usput potvrđuje leaf-priority — leaf-kolizije bi
trebalo da pređu u PASS, a ostaju pogrešan-leaf-id (enum target) + apstinencije.

Canonical setovi se NE diraju (eval-set invariant) — skript samo SELEKTUJE.
Regeneriši:  .venv/bin/python -m scripts.gen_acpt_fails
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "evals" / "runs"
SETS = ROOT / "evals" / "sets"

ACPT_RUN = RUNS / "categories-acpt-full.jsonl"
CANONICAL = SETS / "categories.jsonl"
MANUAL = SETS / "categories_manual.jsonl"
OUT = SETS / "categories_acpt_fails.jsonl"

# Negativci iz manual seta: koliko po subtype-u (not_in_catalog / ambiguous_name /
# typo_likely / out_of_scope) — kontrola da stezanje ne uguši legitimne ne-tool slučajeve.
NEGATIVES_PER_SUBTYPE = 2


def _read_jsonl(path: Path) -> list[dict]:
    """JSONL u listu dict-ova; preskoči // komentare i prazne linije."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("//"):
            rows.append(json.loads(s))
    return rows


def _raw_lines_by_id(path: Path) -> dict[str, str]:
    """{id: sirova JSONL linija} — entry se povlači verbatim, bez re-serializacije."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("//"):
            out[json.loads(s)["id"]] = s
    return out


def main() -> int:
    verdicts = _read_jsonl(ACPT_RUN)
    fails = sorted(r["entry_id"] for r in verdicts if r.get("overall") == "FAIL")

    canonical = _raw_lines_by_id(CANONICAL)
    missing = [e for e in fails if e not in canonical]
    positives = [canonical[e] for e in fails if e in canonical]

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
        "// Auto-generisano iz scripts/gen_acpt_fails.py — ne edituj rukom.\n"
        f"// HARD set: {len(positives)} padova iz {ACPT_RUN.name} (overall=FAIL) "
        f"+ {len(negatives)} negativaca.\n"
        "// Regeneriši: .venv/bin/python -m scripts.gen_acpt_fails\n"
    )
    OUT.write_text(header + "\n".join(positives + negatives) + "\n", encoding="utf-8")

    print(f"[gen_acpt_fails] padova (overall=FAIL): {len(fails)}")
    if missing:
        print(f"[gen_acpt_fails] UPOZORENJE: {len(missing)} padova nije u canonical: {missing}")
    print(f"[gen_acpt_fails] negativaca: {len(negatives)}")
    print(f"[gen_acpt_fails] ukupno u {OUT.name}: {len(positives) + len(negatives)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
