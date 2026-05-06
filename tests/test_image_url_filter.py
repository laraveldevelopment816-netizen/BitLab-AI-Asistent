"""
Test za image_url filter u rag.py (Sesija 8 hotfix).

Webshop ima legacy storage migration — proizvodi sa kratkim cover
prefiksom (npr. "728_lenovo.jpg") imaju 302 redirect na homepage,
proizvodi sa novim 7+ cifrenim prefiksom (npr. "0141906_asus-...")
rade. Audit (scripts/audit_missing_images.py) je pokazao 7.2% missing
slika.

rag.search() sad postavlja image_url=None za:
- Cover sa kratkim/legacy prefiksom (regex `^\\d{7,}_` ne match)
- Sifre eksplicitno u data/missing_images.json
- Bez cover polja
"""
from __future__ import annotations

import json

import pytest

from app.rag import get_index


@pytest.fixture(scope="module")
def idx():
    return get_index()


def test_legacy_cover_naming_yields_none_image(idx):
    """Lenovo IdeaPad Slim 3 i5-13420H ima cover='728_lenovo.jpg' →
    legacy format → image_url mora biti None."""
    results = idx.search("lenovo ideapad slim 3 i5-13420H", top_k=3, category_id="98")
    target = next(
        (r for r in results if "83K1009CSC" in r["name"].upper()),
        None
    )
    assert target is not None, "Test ne nalazi target proizvod u prvih 3 — provjeri eval set"
    assert target["image_url"] is None, (
        f"Legacy cover '728_lenovo.jpg' mora dati image_url=None, "
        f"dobio {target['image_url']!r}"
    )


def test_modern_cover_yields_valid_url(idx):
    """ASUS E1504FA ima cover '0141906_asus-...' (7-cifren prefix) →
    image_url mora biti valid URL."""
    results = idx.search("asus e1504fa", top_k=3, category_id="98")
    target = next(
        (r for r in results if "E1504FA" in r["name"].upper()),
        None
    )
    assert target is not None
    assert target["image_url"] is not None
    assert target["image_url"].startswith("https://webshop.bitlab.rs/files/products/img/")
    assert "0141906_" in target["image_url"] or "0138900_" in target["image_url"]


def test_no_cover_field_yields_none(idx):
    """Ako proizvod nema cover polje uopšte → image_url None."""
    # Idemo kroz prvih 100 proizvoda iz indexa, naći onaj bez cover-a
    no_cover_pid = None
    for pid_str, meta in idx._products.items():
        if not (meta.get("cover") or "").strip():
            no_cover_pid = pid_str
            break

    if no_cover_pid is None:
        pytest.skip("Svi proizvodi u test indeksu imaju cover polje")

    # Pretraži po imenu da dobijemo rezultat
    name = idx._products[no_cover_pid]["name"][:30]
    results = idx.search(name, top_k=10)
    matched = next((r for r in results if r["sifra"] == idx._products[no_cover_pid]["sifra"]), None)
    if matched:
        assert matched["image_url"] is None


def test_missing_images_json_loaded():
    """Audit output je opciono. Ako postoji, mora biti valid JSON sa 'missing' listom."""
    from app.rag import _MISSING_IMAGE_SIFRAS, _MISSING_IMAGES_PATH
    if _MISSING_IMAGES_PATH.exists():
        # Nije prazno → znači da je audit pokrenut i učitan
        assert isinstance(_MISSING_IMAGE_SIFRAS, frozenset)
        # Verifikacija struktura JSON-a
        data = json.loads(_MISSING_IMAGES_PATH.read_text(encoding="utf-8"))
        assert "missing" in data
        assert "checked" in data
        if data["missing"]:
            assert "sifra" in data["missing"][0]


def test_image_filter_does_not_break_other_fields(idx):
    """Filter ne smije uticati na ostala polja rezultata."""
    results = idx.search("laptop", top_k=5, category_id="98")
    assert len(results) > 0
    for r in results:
        assert r["sifra"]
        assert r["name"]
        assert r["price_km"] is not None
        assert "url" in r
        assert "availability" in r
        # image_url može biti None ili string
        assert r["image_url"] is None or r["image_url"].startswith("http")
