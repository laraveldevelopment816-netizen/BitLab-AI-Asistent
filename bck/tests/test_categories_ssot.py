"""
Strukturna provjera SSOT modula `app.categories` — bez direktnog čitanja
taxonomy fajla. Sirov pristup ide kroz `iter_raw_entries()` koji modul
namjerno izlaže za build-time/testing potrebe.

Pokriva refaktor opisan u `SSOT-categories-refactor-plan.md`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app import categories as cats_ssot

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_active_ids_status_filter():
    """ACTIVE_IDS sadrži samo cat-ove sa status=1 iz taxonomy entry-ja.
    Sirov pristup ide preko SSOT-ovog javnog API-ja (`iter_raw_entries`
    sa `active_only=False`), ne čitamo fajl direktno."""
    expected = {cid for cid, c in cats_ssot.iter_raw_entries(active_only=False) if c.get("status") == 1}
    assert cats_ssot.ACTIVE_IDS == expected


def test_all_ids_includes_inactive():
    """ALL_IDS uključuje status=0 i NULL — koristi se kao verifikacija
    drift-a (override fajl smije referencirati nepostojeće, ali ne
    smije imati ne-stringove)."""
    expected = {cid for cid, _ in cats_ssot.iter_raw_entries(active_only=False)}
    assert cats_ssot.ALL_IDS == expected
    assert len(cats_ssot.ALL_IDS) > len(cats_ssot.ACTIVE_IDS), (
        "ALL_IDS treba biti veći od ACTIVE_IDS (status=0 i NULL postoje)."
    )


def test_categories_dict_has_label_for_each_active_id():
    """Svaki cat u CATEGORIES mora imati neprazan label (override → h1
    → name)."""
    assert set(cats_ssot.CATEGORIES.keys()) == cats_ssot.ACTIVE_IDS
    for cid, info in cats_ssot.CATEGORIES.items():
        assert info["label"], f"Cat {cid} nema label."
        assert "parent_id" in info
        assert "count" in info


def test_parent_categories_structure():
    """PARENT_CATEGORIES su parent_id=0 cat-ovi sa ≥2 aktivne djece —
    referentni skup izračunavamo iz iter_raw_entries i poredimo."""
    direct_children: dict[int, list[dict]] = {}
    parents: list[dict] = []
    for _, c in cats_ssot.iter_raw_entries(active_only=True):
        pid = c.get("parent_id")
        if pid == 0:
            parents.append(c)
        elif pid and pid != 0:
            direct_children.setdefault(pid, []).append(c)

    expected_parent_ids = {
        str(p["id"]) for p in parents if len(direct_children.get(p["id"], [])) >= 2
    }
    assert set(cats_ssot.PARENT_CATEGORIES.keys()) == expected_parent_ids

    for pid, p in cats_ssot.PARENT_CATEGORIES.items():
        expected_kids_ids = {str(k["id"]) for k in direct_children.get(int(pid), [])}
        actual_kids_ids = {k["cat_id"] for k in p["children"]}
        assert expected_kids_ids == actual_kids_ids, (
            f"Djeca za parent {pid} se razlikuju."
        )


def test_cat_descendants_includes_self():
    """CAT_DESCENDANTS[cid] uvijek sadrži sam cid."""
    for cid, descendants in cats_ssot.CAT_DESCENDANTS.items():
        assert cid in descendants, f"Cat {cid} nije u svom descendant set-u."


def test_children_of_consistent_with_descendants():
    """CHILDREN_OF (direktna djeca) je strict podskup CAT_DESCENDANTS
    minus sam cat. Za svakog direktnog dijete c od p: c je u
    CAT_DESCENDANTS[p]."""
    for pid, kids in cats_ssot.CHILDREN_OF.items():
        descendants = cats_ssot.CAT_DESCENDANTS.get(pid, set())
        for kid in kids:
            assert kid in descendants, (
                f"Cat {kid} je u CHILDREN_OF[{pid}] ali ne u CAT_DESCENDANTS[{pid}]."
            )


def test_label_overrides_applied():
    """Cat 125 ne postoji u taxonomy-ju (fantom bucket iz legacy fajla);
    nakon refaktora ne smije biti u CATEGORIES (ACTIVE_IDS), ali override
    fajl ga smije sadržati (orphan warning, ne fail).

    Plus: svaki override koji match-uje aktivnu taksonomy kategoriju
    mora biti primijenjen kao label."""
    import json

    overrides_path = PROJECT_ROOT / "data" / "category_label_overrides.json"
    if not overrides_path.exists():
        pytest.skip("category_label_overrides.json mora postojati za ovaj test")
    overrides = json.loads(overrides_path.read_text(encoding="utf-8"))

    assert "125" not in cats_ssot.CATEGORIES, (
        "Cat 125 (fantom bucket iz legacy fajla) ne smije biti aktivan."
    )

    for cid, label in overrides.items():
        if cid in cats_ssot.CATEGORIES:
            assert cats_ssot.CATEGORIES[cid]["label"] == label, (
                f"Override za {cid} nije primijenjen "
                f"(očekivano: '{label}', dobio: '{cats_ssot.CATEGORIES[cid]['label']}')"
            )


def test_get_active_ids_with_products_excludes_zero():
    """Filter `min_products=1` mora eliminisati cat-ove sa count=0."""
    ids = cats_ssot.get_active_ids_with_products(min_products=1)
    for cid in ids:
        assert cats_ssot.CATEGORIES[cid]["count"] >= 1


def test_render_blocks_non_empty():
    """Render-i ne smiju biti prazni."""
    assert cats_ssot.render_categories_block()
    assert cats_ssot.render_parents_block()


def test_iter_raw_entries_active_filter():
    """iter_raw_entries(active_only=True) vraća samo status=1."""
    for cid, c in cats_ssot.iter_raw_entries(active_only=True):
        assert c.get("status") == 1, f"Cat {cid} ima status={c.get('status')} ali je u active iter."
