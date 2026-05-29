"""
Pytest unit testovi za app/tools.py, app/faq.py i app/rag.py.

Pokretanje:
    pytest tests/ -v

Testovi koji zahtijevaju products.index.npz automatski se preskačaju
ako indeks nije generisan (python scripts/embed_products.py).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FAQ_PATH = PROJECT_ROOT / "data" / "faq.md"
INDEX_PATH = PROJECT_ROOT / "data" / "products.index.npz"

needs_index = pytest.mark.skipif(
    not INDEX_PATH.exists(),
    reason="products.index.npz nije generisan — pokreni: python scripts/embed_products.py",
)


# ── FAQ testovi (ne zahtijevaju indeks) ──────────────────────────────────────

class TestFaqLoader:
    def test_loads_sections(self):
        from app.faq import load_faq
        sections = load_faq(FAQ_PATH)
        assert len(sections) >= 3, "FAQ treba imati najmanje 3 sekcije"

    def test_sections_have_title_and_content(self):
        from app.faq import load_faq
        for s in load_faq(FAQ_PATH):
            assert s.title, "Svaka sekcija mora imati naslov"
            assert s.content, "Svaka sekcija mora imati sadržaj"

    def test_search_dostava_returns_match(self):
        from app.faq import load_faq, search_faq
        sections = load_faq(FAQ_PATH)
        results = search_faq(sections, "dostava", top_k=3)
        assert len(results) >= 1
        combined = " ".join(s.content.lower() + s.title.lower() for s in results)
        assert "dostav" in combined

    def test_search_garancija_returns_match(self):
        from app.faq import load_faq, search_faq
        sections = load_faq(FAQ_PATH)
        results = search_faq(sections, "garancija", top_k=3)
        assert len(results) >= 1

    def test_search_empty_query_returns_empty(self):
        from app.faq import load_faq, search_faq
        sections = load_faq(FAQ_PATH)
        assert search_faq(sections, "", top_k=5) == []
        assert search_faq(sections, "   ", top_k=5) == []

    def test_search_top_k_respected(self):
        from app.faq import load_faq, search_faq
        sections = load_faq(FAQ_PATH)
        results = search_faq(sections, "dostava plaćanje garancija kontakt", top_k=2)
        assert len(results) <= 2


# ── Tool dispatcher testovi ───────────────────────────────────────────────────

class TestDispatcher:
    def test_unknown_tool_returns_error(self):
        from app.tools import dispatch
        result = dispatch("nepostojeci_alat", {})
        assert "Nepoznat alat" in result

    def test_escalate_contains_contacts(self):
        from app.tools import handle_escalate_to_human
        result = handle_escalate_to_human(
            reason="b2b_ponuda",
            summary="Klijent traži ponudu za 20 laptopa, ima JIB.",
        )
        assert "066 516 174" in result
        assert "prodaja@bitlab.rs" in result
        assert "b2b_ponuda" in result

    def test_escalate_reklamacija(self):
        from app.tools import handle_escalate_to_human
        result = handle_escalate_to_human(
            reason="reklamacija",
            summary="Monitor ne radi od prvog dana.",
        )
        assert "reklamacija" in result


# ── Testovi pretrage proizvoda (zahtijevaju indeks) ───────────────────────────

class TestProductSearch:
    @needs_index
    def test_returns_list(self):
        from app.tools import handle_search_products
        raw = handle_search_products("SSD 1TB")
        results = json.loads(raw)
        assert isinstance(results, list)
        assert len(results) >= 1

    @needs_index
    def test_result_has_required_fields(self):
        from app.tools import handle_search_products
        results = json.loads(handle_search_products("laptop"))
        for item in results:
            assert "name" in item
            assert "price_km" in item
            assert "availability" in item

    @needs_index
    def test_price_filter_respected(self):
        from app.tools import handle_search_products
        results = json.loads(handle_search_products("laptop", max_price_km=1000.0))
        for item in results:
            if item.get("price_km") is not None:
                assert item["price_km"] <= 1000.0, (
                    f"Rezultat {item['name']} ima cijenu {item['price_km']} > 1000 KM"
                )

    @needs_index
    def test_no_results_returns_string(self):
        from app.tools import handle_search_products
        result = handle_search_products("xyzzy_nema_ovoga_u_katalogu_12345")
        assert isinstance(result, str)

    @needs_index
    def test_top_k_respected(self):
        from app.tools import handle_search_products
        results = json.loads(handle_search_products("monitor", top_k=3))
        assert len(results) <= 3


# ── Testovi provjere dostupnosti ──────────────────────────────────────────────

class TestCheckAvailability:
    @needs_index
    def test_missing_sifra_returns_message(self):
        from app.tools import handle_check_availability
        result = handle_check_availability("NEMA-OVE-SIFRE-XYZ-99999")
        assert "nije pronađen" in result.lower()

    @needs_index
    def test_empty_sifra_returns_message(self):
        from app.tools import handle_check_availability
        result = handle_check_availability("")
        assert isinstance(result, str)
        assert len(result) > 0


# ── FAQ handler testovi (zahtijevaju faq.md ali ne indeks) ───────────────────

class TestGetFaq:
    def test_dostava_tema(self):
        from app.tools import handle_get_faq
        result = handle_get_faq("dostava")
        assert "dostav" in result.lower()

    def test_returns_string(self):
        from app.tools import handle_get_faq
        result = handle_get_faq("garancija servis")
        assert isinstance(result, str)
        assert len(result) > 10

    def test_irrelevant_topic(self):
        from app.tools import handle_get_faq
        result = handle_get_faq("xyzzy_nema")
        assert isinstance(result, str)
