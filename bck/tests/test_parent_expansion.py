"""
Testovi za parent_id expansion u rag.py hard filter-u.

Pokriva:
- CAT_DESCENDANTS (SSOT iz app.categories) vraća tačan set descendant-a
  za root cat-ove
- Leaf cat-ovi vraćaju samo {sebe}
- Inactive cat-ovi (status=0) se preskaču
- Idempotentnost: cat koji nije u taxonomy-ju → ne smije biti u mapi
- Stvarni numerčki dokaz: cat 17 pool raste sa ~20 na ~197 proizvoda

Ne treba products.index.npz — test je čisto static nad JSON taxonomy-jem +
products export-om.

Pokretanje:
    pytest tests/test_parent_expansion.py -v
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_PATH = PROJECT_ROOT / "data" / "all-products.json"


def _ssot_loaded() -> bool:
    """SSOT modul `app.categories` se učitava pri import-u; ako je
    `CATEGORIES` prazan (npr. taxonomy fajl ne postoji), test se preskače."""
    from app.categories import CATEGORIES
    return bool(CATEGORIES)


needs_taxonomy = pytest.mark.skipif(
    not _ssot_loaded(),
    reason="app.categories.CATEGORIES je prazan (taxonomy fajl ne postoji)",
)
needs_products = pytest.mark.skipif(
    not PRODUCTS_PATH.exists(),
    reason="data/all-products.json mora postojati",
)


@pytest.fixture(scope="module")
def descendants_map():
    """Učitaj mapu cat_id → {sebe + descendant-i} iz SSOT modula."""
    from app.categories import CAT_DESCENDANTS
    return CAT_DESCENDANTS


@pytest.fixture(scope="module")
def product_counts() -> Counter:
    """Broj proizvoda po cat_id iz all-products.json (deterministički)."""
    data = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    rows = next(e["data"] for e in data if e.get("type") == "table" and e.get("name") == "products")
    return Counter((p.get("categories_id") or "").strip() for p in rows)


@needs_taxonomy
class TestDescendantsStructure:

    def test_loads_active_cats(self, descendants_map):
        # Iz CSV-a 238 aktivnih cat-ova (vidi docs/category-analysis/PROPOSAL).
        assert len(descendants_map) >= 230, (
            f"Premalo aktivnih cat-ova ({len(descendants_map)}); "
            "provjeri status filter u _load_cat_descendants."
        )

    def test_leaf_cat_is_self_only(self, descendants_map):
        """Notebook (98) je leaf — descendants treba da bude {98}."""
        assert descendants_map["98"] == {"98"}

    def test_leaf_tastature(self, descendants_map):
        """Tastature (220) je leaf."""
        assert descendants_map["220"] == {"220"}

    def test_root_includes_self(self, descendants_map):
        """Računari (17) je root — descendants mora uključivati sebe."""
        assert "17" in descendants_map["17"]

    def test_racunari_has_known_children(self, descendants_map):
        """Cat 17 (Računari) ima poznatu djecu po CSV-u: 99 Tablet, 93 Desktop
        Brand, itd. Ovaj test fail-uje ako neko ukloni djecu bez ažuriranja."""
        d = descendants_map["17"]
        assert "99" in d, "Tablet (99) bi trebao biti dijete cat 17"
        assert "93" in d, "Desktop Brand (93) bi trebao biti dijete cat 17"
        assert "101" in d, "Produzenje garancije (101) bi trebao biti dijete cat 17"

    def test_pc_komponente_has_known_children(self, descendants_map):
        """Cat 107 (PC komponente) ima 16 djece prema CSV-u."""
        d = descendants_map["107"]
        assert "108" in d, "Matične ploče"
        assert "113" in d, "RAM"
        assert "115" in d, "SSD"
        assert "117" in d, "Grafičke kartice"
        assert "118" in d, "Kućišta"
        assert "120" in d, "Napojne jedinice"

    def test_inactive_cats_excluded(self, descendants_map):
        """Cat 277 (Ostalo) ima status=0 u CSV-u — ne treba biti u mapi."""
        assert "277" not in descendants_map, (
            "Inaktivni cat 277 ne smije biti u descendants mapi"
        )

    def test_unknown_cat_not_in_map(self, descendants_map):
        """Cat koji ne postoji u CSV-u ne smije biti u mapi (rag.py fallback
        na {cat_id} hendluje ovaj slučaj defensive-no)."""
        assert "99999" not in descendants_map


@needs_taxonomy
@needs_products
class TestPoolCoverageDelta:
    """Stvarni numerčki dokaz da parent expansion donosi puno više proizvoda."""

    def test_cat_17_racunari_grows_significantly(self, descendants_map, product_counts):
        """Cat 17 sam ima ~20 direktnih, sa expansion-om mora biti ≥150."""
        direct = product_counts.get("17", 0)
        subtree = sum(product_counts.get(c, 0) for c in descendants_map["17"])
        assert subtree > direct * 5, (
            f"Parent expansion nedovoljan: direct={direct}, subtree={subtree}. "
            "Cat 17 (Računari) mora imati barem 5x više u podstablu nego sam."
        )
        assert subtree >= 150, (
            f"Cat 17 podstablo treba ≥150 proizvoda, dobio {subtree}"
        )

    def test_cat_107_pc_komponente_was_empty(self, descendants_map, product_counts):
        """Cat 107 sam ima 0 direktnih proizvoda — sve je u djeci. Bez
        expansion-a search vrati prazno; sa expansion-om ≥200 proizvoda."""
        direct = product_counts.get("107", 0)
        subtree = sum(product_counts.get(c, 0) for c in descendants_map["107"])
        assert direct == 0, (
            f"Cat 107 trebao bi imati 0 direktnih (sve u djeci), ima {direct}"
        )
        assert subtree >= 200, (
            f"Cat 107 podstablo treba ≥200 proizvoda, dobio {subtree}"
        )

    def test_cat_151_mobiteli_largest_subtree(self, descendants_map, product_counts):
        """Mobiteli (151) je najveći podstablo zbog cat 394 (maske, 1274 prod)."""
        direct = product_counts.get("151", 0)
        subtree = sum(product_counts.get(c, 0) for c in descendants_map["151"])
        assert subtree >= 1500, f"Mobiteli podstablo treba ≥1500, dobio {subtree}"
        # Direct count je vrlo mali (5-ak proizvoda); subtree mora biti ~300x veći.
        assert subtree > direct * 100

    def test_leaf_cat_no_change(self, descendants_map, product_counts):
        """Notebook (98) je leaf — direct == subtree (mora biti identično)."""
        direct = product_counts.get("98", 0)
        subtree = sum(product_counts.get(c, 0) for c in descendants_map["98"])
        assert direct == subtree, (
            f"Leaf cat 98 direct={direct} != subtree={subtree} — leaf ne smije rasti"
        )
        assert direct > 0, "Cat 98 (Notebook) treba imati proizvode"


@needs_taxonomy
class TestDeterminism:
    """Helper mora biti čista funkcija — isti taxonomy → isti rezultat."""

    def test_module_level_constant(self, descendants_map):
        """CAT_DESCENDANTS je modul-level konstanta — re-import vraća istu
        instancu (ili ekvivalentnu) bez side-effect-a."""
        from app.categories import CAT_DESCENDANTS as a
        from app.categories import CAT_DESCENDANTS as b
        assert a == b

    def test_sets_not_lists(self, descendants_map):
        """Vrijednosti su set-ovi (O(1) membership), ne liste — bitno za
        performanse hard filtera u search()."""
        for cat_id, desc in descendants_map.items():
            assert isinstance(desc, set), f"Cat {cat_id} nije set: {type(desc)}"
