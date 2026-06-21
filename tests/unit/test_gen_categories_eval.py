"""Unit testovi za scripts/gen_categories_eval.py — schema + determinizam.

Memorija test_case_invariant: ne diramo eval entry-je sa kojima radi runner;
ovi testovi validuju da generator pravi entry-je koji prate EvalEntry schemu.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evals.framework import loader
from scripts.gen_categories_eval import (
    HEADER_LINES,
    generate_entries,
    render_jsonl,
)

pytestmark = pytest.mark.unit


SAMPLE_CATEGORIES: list[dict] = [
    {"id": 1, "name": "Racunari", "parent_id": 0},  # parent: 2 djece (2, 3) → overview
    {"id": 2, "name": "Desktop", "parent_id": 1},  # leaf
    {"id": 3, "name": "Laptop", "parent_id": 1},  # leaf
    {"id": 4, "name": "Lonely Leaf", "parent_id": 0},  # root leaf bez djece
    {"id": 5, "name": "Parent sa 1 djetetom", "parent_id": 0},  # 1 dijete → skip
    {"id": 6, "name": "Solo dijete", "parent_id": 5},  # leaf
    {"id": 7, "name": "Tri-djece parent", "parent_id": 0},  # 3 djece → overview
    {"id": 8, "name": "Dijete 7a", "parent_id": 7},
    {"id": 9, "name": "Dijete 7b", "parent_id": 7},
    {"id": 10, "name": "Dijete 7c", "parent_id": 7},
]


# --------------------------- routing pravila ---------------------------


def test_leaf_dobija_search_products_entry() -> None:
    entries = generate_entries(SAMPLE_CATEGORIES)
    by_id = {e["id"]: e for e in entries}
    leaf = by_id["cat-leaf-2"]
    assert leaf["expect"]["tool"] == "search_products"
    assert leaf["expect"]["args_subset"] == {"category_id": 2}
    assert leaf["tags"] == ["auto-gen", "leaf"]
    assert leaf["query"] == "Desktop"


def test_parent_sa_2plus_djece_dobija_category_overview() -> None:
    entries = generate_entries(SAMPLE_CATEGORIES)
    by_id = {e["id"]: e for e in entries}
    parent = by_id["cat-parent-1"]
    assert parent["expect"]["tool"] == "category_overview"
    assert parent["expect"]["args_subset"] == {"category_id": 1}
    assert parent["tags"] == ["auto-gen", "parent"]
    assert parent["query"] == "Racunari"


def test_parent_sa_1_djetetom_se_preskace() -> None:
    entries = generate_entries(SAMPLE_CATEGORIES)
    ids = {e["id"] for e in entries}
    assert "cat-parent-5" not in ids
    assert "cat-leaf-5" not in ids


def test_solo_dijete_se_tretira_kao_leaf() -> None:
    entries = generate_entries(SAMPLE_CATEGORIES)
    ids = {e["id"] for e in entries}
    assert "cat-leaf-6" in ids


def test_root_bez_djece_je_leaf() -> None:
    entries = generate_entries(SAMPLE_CATEGORIES)
    by_id = {e["id"]: e for e in entries}
    assert "cat-leaf-4" in by_id
    assert by_id["cat-leaf-4"]["expect"]["tool"] == "search_products"


def test_parent_sa_3_djece_dobija_overview_djeca_su_leaves() -> None:
    entries = generate_entries(SAMPLE_CATEGORIES)
    by_id = {e["id"]: e for e in entries}
    assert "cat-parent-7" in by_id
    for child_id in (8, 9, 10):
        assert f"cat-leaf-{child_id}" in by_id


# --------------------------- schema invariant ---------------------------


def test_entry_ima_obavezna_polja_iz_EvalEntry_scheme() -> None:
    entries = generate_entries(SAMPLE_CATEGORIES)
    assert entries, "sample mora generisati bar jedan entry"
    for e in entries:
        assert isinstance(e["id"], str) and e["id"]
        assert isinstance(e["query"], str) and e["query"]
        assert e["history"] == []
        assert isinstance(e["expect"], dict)
        assert e["expect"]["tool"] in {"search_products", "category_overview"}
        assert "category_id" in e["expect"]["args_subset"]
        assert "auto-gen" in e["tags"]


def test_entries_su_sortirane_po_category_id() -> None:
    entries = generate_entries(SAMPLE_CATEGORIES)
    cat_ids = [e["expect"]["args_subset"]["category_id"] for e in entries]
    assert cat_ids == sorted(cat_ids)


# --------------------------- determinizam ---------------------------


def test_render_je_byte_identican_na_uzastopnim_pozivima() -> None:
    a = render_jsonl(generate_entries(SAMPLE_CATEGORIES))
    b = render_jsonl(generate_entries(SAMPLE_CATEGORIES))
    assert a == b


def test_render_je_byte_identican_kada_se_input_preuredi() -> None:
    """Redoslijed kategorija u inputu ne smije promijeniti output."""
    a = render_jsonl(generate_entries(SAMPLE_CATEGORIES))
    reordered = list(reversed(SAMPLE_CATEGORIES))
    b = render_jsonl(generate_entries(reordered))
    assert a == b


def test_render_sadrzi_header_komentare() -> None:
    out = render_jsonl(generate_entries(SAMPLE_CATEGORIES))
    for header in HEADER_LINES:
        assert header in out


# --------------------------- integration sa loader-om ---------------------------


def test_output_je_parseabilan_kroz_loader(tmp_path: Path) -> None:
    out = render_jsonl(generate_entries(SAMPLE_CATEGORIES))
    suite = tmp_path / "categories_sample.jsonl"
    suite.write_text(out, encoding="utf-8")

    loaded = loader.load_suite(suite)
    assert loaded, "loader mora vratiti bar jedan entry"
    for entry in loaded:
        assert entry["id"].startswith("cat-")
        assert entry["expect"]["tool"] in {"search_products", "category_overview"}


# --------------------------- acceptance protiv pravih podataka ---------------------------

REAL_CATEGORIES_PATH = Path(__file__).resolve().parents[2] / "data" / "categories_new.json"


@pytest.mark.skipif(
    not REAL_CATEGORIES_PATH.exists(),
    reason=f"{REAL_CATEGORIES_PATH} not present (vidi specs/categories.md §1)",
)
def test_pravi_podaci_generisu_30_plus_entry_ja() -> None:
    with REAL_CATEGORIES_PATH.open(encoding="utf-8") as f:
        cats = json.load(f)
    entries = generate_entries(cats)
    assert len(entries) >= 30, f"acceptance Now task 1: ≥30 entry-ja, dobijeno {len(entries)}"


@pytest.mark.skipif(
    not REAL_CATEGORIES_PATH.exists(),
    reason=f"{REAL_CATEGORIES_PATH} not present",
)
def test_pravi_podaci_byte_identican_render() -> None:
    with REAL_CATEGORIES_PATH.open(encoding="utf-8") as f:
        cats = json.load(f)
    a = render_jsonl(generate_entries(cats))
    b = render_jsonl(generate_entries(cats))
    assert a == b
