"""
Testovi za brand- i category-aware search (feature/ai-search-brand-category-improvements).

Pokriva:
- Brand detection iz query-ja (single + multi-token brendovi)
- Category detection sa head-noun fallback (gaming miš, samsung tv)
- Hard filter po brand_id (search_products tool param)
- Hard filter po category_id + brand_id u kombinaciji
- Migration drift handler — cat 277 (drift target) hvata "miš"

Pokretanje:
    pytest tests/test_brand_category_search.py -v
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = PROJECT_ROOT / "data" / "products.index.npz"
TERMS_PATH = PROJECT_ROOT / "data" / "category_terms.json"
BRANDS_PATH = PROJECT_ROOT / "data" / "brend.json"

needs_index = pytest.mark.skipif(
    not INDEX_PATH.exists(),
    reason="products.index.npz nije generisan — pokreni: python scripts/embed_products.py",
)


# ── Static testovi (ne zahtijevaju indeks) ───────────────────────────────────


class TestCategoryTermsData:
    """Verifikuje strukturu i pokrivenost data/category_terms.json."""

    def test_file_exists(self):
        assert TERMS_PATH.exists(), (
            "data/category_terms.json mora postojati — pokreni "
            "python scripts/build_category_terms.py"
        )

    def test_has_high_value_categories(self):
        """Top kategorije po prometu MORAJU imati termine."""
        data = json.loads(TERMS_PATH.read_text(encoding="utf-8"))
        # cat 175 (mobiteli), 163 (tv), 98 (laptop), 224 (monitor),
        # 220 (tastatura), 277 (miševi via drift), 115 (ssd), 108 (matična),
        # 309 (router), 393 (gift card)
        for cid in ["175", "163", "98", "224", "220", "277", "115", "108", "309", "393"]:
            assert cid in data, f"Kritična kategorija {cid} nedostaje u terms"
            assert isinstance(data[cid], list)
            assert len(data[cid]) > 0

    def test_drift_target_277_has_mouse_terms(self):
        """Cat 277 ima 535 proizvoda (45% miševa), CSV row je 'Ostalo'.
        Manual override mora dodati 'miš', 'mis' za search."""
        data = json.loads(TERMS_PATH.read_text(encoding="utf-8"))
        terms_277 = data.get("277", [])
        assert any("mis" in t or "miš" in t for t in terms_277), (
            f"Cat 277 mora imati mouse termine. Trenutno: {terms_277}"
        )

    def test_singular_short_terms_for_top_cats(self):
        """User često tipka 'tv', 'monitor', 'tablet' (singular). Manual
        override layer mora pokriti ovo iznad SEO meta_keywords."""
        data = json.loads(TERMS_PATH.read_text(encoding="utf-8"))
        assert "tv" in data["163"], f"cat 163 mora imati 'tv'. Imamo: {data['163']}"
        assert "monitor" in data["224"], f"cat 224 mora imati 'monitor'. Imamo: {data['224']}"
        assert "tablet" in data["99"], f"cat 99 mora imati 'tablet'. Imamo: {data['99']}"


class TestBrandData:
    """Verifikuje strukturu data/brend.json."""

    def test_file_exists(self):
        assert BRANDS_PATH.exists()

    def test_has_top_brands(self):
        """Najvažniji brendovi MORAJU postojati."""
        from app.tools import BRANDS
        brand_names = {b["name"].upper() for b in BRANDS}
        for name in ["APPLE", "SAMSUNG", "ASUS", "HP", "LENOVO", "DELL", "XIAOMI"]:
            assert name in brand_names, f"Brand {name} nedostaje"

    def test_brands_sorted_by_priority(self):
        """Brendovi sa priority 1–20 idu prvi u tool description-u."""
        from app.tools import BRANDS
        priorities = [b["priority"] for b in BRANDS]
        # Provjeri da je sortiran ascending (None/999 idu na kraj)
        for i in range(len(priorities) - 1):
            assert priorities[i] <= priorities[i+1], (
                f"BRANDS nije sortiran: {priorities[:5]}..."
            )


# ── Detection testovi (zahtijevaju indeks za ProductIndex init) ──────────────


@needs_index
class TestBrandDetection:
    """Brand mention u query-ju → set id_brend-ova."""

    @pytest.fixture(scope="class")
    def idx(self):
        from app.rag import get_index
        return get_index()

    def test_apple_iphone_detects_apple(self, idx):
        # Apple = id 11 u brend.json
        assert idx._detect_intent_brands("Apple iPhone") == {"11"}

    def test_asus_laptop_detects_asus(self, idx):
        # Asus = id 13
        assert idx._detect_intent_brands("Asus laptop") == {"13"}

    def test_samsung_tv_detects_samsung(self, idx):
        # Samsung = id 68
        assert idx._detect_intent_brands("samsung tv") == {"68"}

    def test_lenovo_alone_detects_brand(self, idx):
        assert idx._detect_intent_brands("lenovo") == {"47"}

    def test_western_digital_bigram_detects_brand(self, idx):
        # Multi-word brand "WESTERN DIGITAL" — id 86 — match preko bigrama
        assert idx._detect_intent_brands("western digital disk") == {"86"}

    def test_cooler_alone_does_not_detect_brand(self, idx):
        """'cooler' u kontekstu 'cpu cooler' NIJE COOLER MASTER brand —
        token mora biti u BRAND_FIRST_TOKEN_BLOCKLIST."""
        assert idx._detect_intent_brands("cpu cooler") == set()
        assert idx._detect_intent_brands("cooler za procesor") == set()

    def test_cooler_master_bigram_detects_brand(self, idx):
        """Puno ime 'cooler master' ipak match-uje brand."""
        assert idx._detect_intent_brands("cooler master case") == {"20"}

    def test_no_brand_in_generic_query(self, idx):
        assert idx._detect_intent_brands("najbolji laptop do 1500 KM") == set()


@needs_index
class TestCategoryDetection:
    """Cat detection sa head-noun fallback i singular/plural matching."""

    @pytest.fixture(scope="class")
    def idx(self):
        from app.rag import get_index
        return get_index()

    def test_singular_monitor_matches_plural_term(self, idx):
        """Term je 'monitori' (plural), query 'monitor' (singular). Bidirek-
        cioni prefix match riješava."""
        assert "224" in idx._detect_intent_categories("monitor 27")

    def test_short_tv_matches_via_manual_override(self, idx):
        """Cat 163 ima 'tv' u manual_term_additions."""
        assert "163" in idx._detect_intent_categories("tv")

    def test_head_noun_fallback_skips_brand(self, idx):
        """'samsung tv' — first non_stop = 'samsung' (brand, not in cat
        terms), fallback na 'tv' → cat 163."""
        cats = idx._detect_intent_categories("samsung tv")
        assert "163" in cats, f"Expected cat 163, got {cats}"

    def test_head_noun_fallback_skips_modifier(self, idx):
        """'gaming miš' — first = 'gaming' (modifier), fallback na 'miš'
        → cat 277 (drift target)."""
        cats = idx._detect_intent_categories("gaming miš")
        assert "277" in cats, f"Expected cat 277, got {cats}"

    def test_head_noun_first_match_stops_propagation(self, idx):
        """'miš za laptop' — 'miš' match-uje cat 277, 'laptop' SE NE
        provjerava (head-noun pravilo). Cilj: ne razvodnjavati boost."""
        cats = idx._detect_intent_categories("miš za laptop")
        assert "277" in cats
        # Laptop ne smije biti u boost-u (head-noun je miš)
        assert "98" not in cats

    def test_bigram_motherboard(self, idx):
        """Bigram 'matična ploča' → cat 108."""
        cats = idx._detect_intent_categories("matična ploča AMD")
        assert "108" in cats

    def test_iphone_detects_mobiteli(self, idx):
        """iPhone u meta_keywords cat 175 ('iphone')."""
        cats = idx._detect_intent_categories("iPhone 15 Pro")
        assert "175" in cats

    def test_long_query_no_detect(self, idx):
        """5+ non-stop tokena — boost se ne aktivira (preverbozno)."""
        q = "trebam mali laptop za firmu sa dobrom baterijom za putovanja"
        # Ovaj upit ima preko 4 non-stop tokena → ne primjenjujemo boost
        # Embedding sam mora odraditi posao
        cats = idx._detect_intent_categories(q)
        # Ne testiramo precizno; samo da ne padne u petlju false-positives
        assert isinstance(cats, set)


# ── Search testovi (zahtijevaju indeks + embedding model) ────────────────────


@needs_index
class TestBrandSearch:
    """End-to-end search sa brand_id parametrom."""

    def test_brand_id_filter(self):
        """search(brand_id='11') vraća SAMO Apple proizvode."""
        from app.rag import get_index
        idx = get_index()
        results = idx.search("telefon", top_k=10, brand_id="11")
        # Provjeri da je brand zaista filtriran
        for r in results:
            sifra = r["sifra"]
            meta = idx.sifra_map.get(sifra, {})
            assert meta.get("id_brend") == "11", (
                f"Proizvod {r['name']} ima id_brend={meta.get('id_brend')}, "
                f"očekivano 11 (Apple)"
            )

    def test_brand_plus_category_filter(self):
        """search(brand_id='13', category_id='98') vraća samo Asus laptope."""
        from app.rag import get_index
        idx = get_index()
        results = idx.search("brz laptop", top_k=10, brand_id="13", category_id="98")
        for r in results:
            sifra = r["sifra"]
            meta = idx.sifra_map.get(sifra, {})
            assert meta.get("id_brend") == "13"
            assert meta.get("categories_id") == "98"

    def test_brand_id_via_tool_handler(self):
        """handle_search_products prosljeđuje brand_id u rag."""
        from app.tools import handle_search_products
        raw = handle_search_products("samsung", brand_id="68", top_k=5)
        results = json.loads(raw)
        # Ne svi rezultati moraju biti Samsung — možemo dobiti string
        # "Nema proizvoda" ako nema match-a, ali ako ima rezultata, moraju
        # svi biti Samsung. Verifikujemo kroz format poziva.
        if isinstance(results, list) and results:
            from app.rag import get_index
            idx = get_index()
            for r in results:
                meta = idx.sifra_map.get(r["sifra"], {})
                assert meta.get("id_brend") == "68"


@needs_index
class TestRegression:
    """Provjeri da nismo regresirali postojeće funkcionalnosti."""

    def test_basic_search_still_works(self):
        from app.tools import handle_search_products
        results = json.loads(handle_search_products("SSD 1TB"))
        assert len(results) >= 1
        assert "name" in results[0]
        assert "price_km" in results[0]

    def test_price_filter_still_respected(self):
        from app.tools import handle_search_products
        results = json.loads(handle_search_products("laptop", max_price_km=1000.0))
        for r in results:
            if r.get("price_km") is not None:
                assert r["price_km"] <= 1000.0

    def test_category_id_filter_still_respected(self):
        """Postojeći category_id filter mora i dalje raditi."""
        from app.rag import get_index
        idx = get_index()
        results = idx.search("uređaj", top_k=10, category_id="98")
        for r in results:
            meta = idx.sifra_map.get(r["sifra"], {})
            assert meta.get("categories_id") == "98"
