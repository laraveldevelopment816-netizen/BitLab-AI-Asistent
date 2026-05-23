"""Zajednički CLI filteri za eval engine alate (run_categories.py,
run_products.py).

Dva alata dijele identičnu semantiku za --ids / --tag / --query:
- `--ids` — comma-list i/ili inclusive range na 4-cifrenim ID-evima.
- `--tag` — može više puta, AND presjek.
- `--query` — ad-hoc upit van seta (override cijelog seta).
"""
from __future__ import annotations


def parse_ids_spec(spec: str) -> set[str]:
    """Parsira `--ids` spec u set 4-cifrenih string ID-eva.

    Format: comma-separated lista, svaki element je ili pojedinačni ID
    (`0007`) ili inclusive range (`0001-0009`). Whitespace dozvoljen.
    Numerički ulaz se normalizuje na 4 cifre (`7` → `0007`).

    Primjeri:
        "0007"             → {"0007"}
        "0001,0023,0091"   → {"0001", "0023", "0091"}
        "0001-0009"        → {"0001", ..., "0009"}
        "0001-0003,0050"   → {"0001", "0002", "0003", "0050"}
    """
    out: set[str] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo_s, hi_s = chunk.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
            for n in range(lo, hi + 1):
                out.add(f"{n:04d}")
        else:
            try:
                out.add(f"{int(chunk):04d}")
            except ValueError:
                out.add(chunk)
    return out


def apply_filters(queries: list[dict], args) -> list[dict]:
    """Apply --query / --ids / --tag filtere.

    Pravila:
    - `--query` je ad-hoc; zamjenjuje cijeli set jednim pseudo-entry-jem
      sa `id="ADHOC"`. Ne kombinuje se sa drugim filterima.
    - `--ids` i `--tag` se mogu kombinovati — presjek (AND).
    - Bez ijedan flag-a: vraća se `queries` neizmijenjen.
    """
    if getattr(args, "query", None):
        return [{
            "id": "ADHOC",
            "query": args.query,
            "history": [],
            "expect": {},
            "tags": ["adhoc"],
        }]
    out = queries
    if getattr(args, "ids", None):
        wanted = parse_ids_spec(args.ids)
        out = [q for q in out if q.get("id") in wanted]
    for t in (getattr(args, "tag", None) or []):
        out = [q for q in out if t in (q.get("tags") or [])]
    return out
