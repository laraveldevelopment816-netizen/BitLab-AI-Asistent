"""Auto-gen kategorija eval set iz data/categories_new.json.

Pravila (specs/categories.md §2):
- Leaf (kategorija bez djece) → entry {tool: "search_products", args.category_id}.
- Parent sa ≥2 djece → entry {tool: "category_overview", args.category_id}.
- Parent sa tačno 1 djetetom → preskoči (spec ne pokriva).
- Query = ime kategorije; history = []; tags = ["auto-gen", "leaf"|"parent"].

Determinizam (specs/categories.md §2): isti input JSON → byte-identical JSONL.
Verifikuje se unit testom u tests/unit/test_gen_categories_eval.py.

Pokretanje:
    python -m scripts.gen_categories_eval
    python scripts/gen_categories_eval.py --input data/categories_new.json --output evals/sets/categories.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = REPO_ROOT / "data" / "categories_new.json"
DEFAULT_OUTPUT = REPO_ROOT / "evals" / "sets" / "categories.jsonl"

# Header se prepiše svaki put — konstantan string => ne razbija determinizam.
HEADER_LINES: tuple[str, ...] = (
    "// Auto-generisano iz scripts/gen_categories_eval.py — ne edituj rukom.",
    "// Source: data/categories_new.json (SSOT). Regeneriši sa:",
    "//   python -m scripts.gen_categories_eval",
    "// Pravila: specs/categories.md §2. Komentari (//) i prazne linije se ignorišu.",
)


def generate_entries(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Konstruiše listu eval entry-ja iz liste kategorija.

    Entry-ji su sortirani po category ID rastuće — bazni nivo determinizma.
    """
    children_by_parent: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for cat in categories:
        children_by_parent[int(cat["parent_id"])].append(cat)

    entries: list[dict[str, Any]] = []
    for cat in sorted(categories, key=lambda c: int(c["id"])):
        cat_id = int(cat["id"])
        name = str(cat["name"]).strip()
        children = children_by_parent.get(cat_id, [])

        if not children:
            entries.append(_leaf_entry(cat_id, name))
        elif len(children) >= 2:
            entries.append(_parent_entry(cat_id, name))
        # parent sa tačno 1 djetetom: spec ne pokriva — preskoči.

    return entries


def _leaf_entry(cat_id: int, name: str) -> dict[str, Any]:
    return {
        "id": f"cat-leaf-{cat_id}",
        "query": name,
        "history": [],
        "expect": {
            "tool": "search_products",
            "args_subset": {"category_id": cat_id},
        },
        "tags": ["auto-gen", "leaf"],
    }


def _parent_entry(cat_id: int, name: str) -> dict[str, Any]:
    return {
        "id": f"cat-parent-{cat_id}",
        "query": name,
        "history": [],
        "expect": {
            "tool": "category_overview",
            "args_subset": {"category_id": cat_id},
        },
        "tags": ["auto-gen", "parent"],
    }


def render_jsonl(entries: list[dict[str, Any]]) -> str:
    """Renderuje entries u JSONL string sa header komentarima.

    sort_keys=True i konstantni separators garantuju byte-stabilan output
    između poziva nad istim ulazom.
    """
    lines: list[str] = list(HEADER_LINES)
    for entry in entries:
        lines.append(json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return "\n".join(lines) + "\n"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Putanja do categories_new.json (default: {DEFAULT_INPUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Putanja do output JSONL (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    with args.input.open("r", encoding="utf-8") as f:
        categories = json.load(f)

    entries = generate_entries(categories)
    output_text = render_jsonl(entries)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output_text, encoding="utf-8")

    leaves = sum(1 for e in entries if "leaf" in e["tags"])
    parents = sum(1 for e in entries if "parent" in e["tags"])
    print(f"Wrote {len(entries)} entries to {args.output} ({leaves} leaves, {parents} parents)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
