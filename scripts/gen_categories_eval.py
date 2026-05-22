"""gen_categories_eval.py — generiše evals/sets/categories_cold.json.

Pozitivni (auto-gen) iz `data/categories_new.json`:
- aktivne (status=1) kategorije
- leaf (0 djece) → expected tool=search_products, category_id=<self>
- parent (≥2 djece) → expected tool=category_overview, category_id=<self>
- parent sa 1 djetetom — preskočeno (schema enum za overview ne dozvoljava,
  a fallback na search_products(parent_id) je dvoznačan; rješava se posebno)

Negativni (ručni, NEGATIVE_EXAMPLES) — pojmovi koji nisu validne kategorije:
- not_in_catalog — pojam koji BitLab ne nosi ("automobili", "knjige")
- ambiguous_name — naziv koji se preklapa sa više pojmova ("kabl", "torba")
- typo_likely — vjerovatna typo greška ("mobitejli", "raunari")
- out_of_scope — politika/FAQ, ne kategorija ("povraćaj robe", "garancija")

Tags razdvajaju izvor (auto-gen | manual) i tip (leaf | parent | negative + razlog).

Upotreba:
    python scripts/gen_categories_eval.py
"""

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATS_PATH = ROOT / "data" / "categories_new.json"
OUT_PATH = ROOT / "evals" / "sets" / "categories_cold.json"


# Ručno održavani negativni primjeri — engine ih očekuje da padnu sa
# eksplicitnim failure_reason. Tako razlikujemo "sistem pravilno odbio"
# od "sistem ne razumije šta tražimo".
NEGATIVE_EXAMPLES: list[dict] = [
    # not_in_catalog — pojam koji BitLab katalog ne nosi
    {"query": "automobili", "failure_reason": "not_in_catalog"},
    {"query": "namještaj", "failure_reason": "not_in_catalog"},
    {"query": "knjige", "failure_reason": "not_in_catalog"},
    # ambiguous_name — naziv koji se preklapa sa više pojmova u katalogu
    {"query": "kabl", "failure_reason": "ambiguous_name"},
    {"query": "torba", "failure_reason": "ambiguous_name"},
    # typo_likely — vjerovatna typografska greška
    {"query": "mobitejli", "failure_reason": "typo_likely"},
    {"query": "raunari", "failure_reason": "typo_likely"},
    # out_of_scope — pojam koji nije kategorija (FAQ/politika)
    {"query": "povraćaj robe", "failure_reason": "out_of_scope"},
    {"query": "garancija", "failure_reason": "out_of_scope"},
    {"query": "dostava", "failure_reason": "out_of_scope"},
]


def main() -> int:
    cats = json.loads(CATS_PATH.read_text(encoding="utf-8"))
    active = [c for c in cats if c.get("status") == 1]

    # parent_id → [child_id, ...]
    children: dict[int, list[int]] = defaultdict(list)
    for c in active:
        pid = c.get("parent_id")
        if pid is not None and pid != 0:
            children[pid].append(c["id"])

    positives: list[dict] = []
    skipped_1child: list[tuple[int, str]] = []

    for c in active:
        cid = c["id"]
        name = c["name"]
        kids = children.get(cid, [])

        if len(kids) == 0:
            entry = {
                "query": name,
                "history": [],
                "expect": {"tool": "search_products", "category_id": str(cid)},
                "tags": ["auto-gen", "leaf"],
            }
            positives.append(entry)
        elif len(kids) >= 2:
            entry = {
                "query": name,
                "history": [],
                "expect": {"tool": "category_overview", "category_id": str(cid)},
                "tags": ["auto-gen", "parent"],
            }
            positives.append(entry)
        else:
            skipped_1child.append((cid, name))

    negatives: list[dict] = []
    for neg in NEGATIVE_EXAMPLES:
        entry = {
            "query": neg["query"],
            "history": [],
            "expect": {"failure_reason": neg["failure_reason"], "tool": None},
            "tags": ["manual", "negative", neg["failure_reason"]],
        }
        negatives.append(entry)

    all_entries = positives + negatives

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(all_entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    leaf_n = sum(1 for e in positives if "leaf" in e["tags"])
    parent_n = sum(1 for e in positives if "parent" in e["tags"])
    print(f"Aktivnih kategorija: {len(active)}")
    print(f"Pozitivni (auto-gen): {len(positives)} ({leaf_n} leaf, {parent_n} parent)")
    print(f"Preskočeno (1 dijete, ambiguous): {len(skipped_1child)}")
    for cid, name in skipped_1child:
        print(f"  - {cid}: {name}")
    print(f"Negativni (ručni): {len(negatives)}")
    print(f"Ukupno entry-ja: {len(all_entries)}")
    print(f"Output: {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
