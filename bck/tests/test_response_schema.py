"""
Unit testovi za strukturisani AI output shemu (`app/schemas.py`, STATUS srcv).

Pokrivaju:
- Validan products / empty / message payload se uspješno parsira u tačnu klasu.
- Empty `products` lista odbijena (za 0 rezultata koristi se EmptyResponse).
- Nedostajuća required polja → ValidationError sa jasnim pointerom.
- `image_url=null` se prihvata (legacy/missing slike).
- Nepoznat `type` u discriminatoru → ValidationError.
- Wrong tipovi (price_km kao string) coerce-uju samo gdje je smisleno.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    EmptyResponse,
    MessageResponse,
    ProductsResponse,
    assistant_response_adapter,
)


class TestProductsResponse:
    def test_valid_products_passes(self):
        data = {
            "type": "products",
            "text": "Evo top 3 laptopa do 1500 KM.",
            "products": [
                {
                    "sifra": "G61839",
                    "name": "ASUS E1504FA 15.6\"",
                    "price_km": 929,
                    "availability": "Na lageru",
                    "url": "https://webshop.bitlab.rs/G61839.html",
                    "image_url": "https://webshop.bitlab.rs/files/products/img/0141906_asus.jpg",
                }
            ],
        }
        r = assistant_response_adapter.validate_python(data)
        assert isinstance(r, ProductsResponse)
        assert r.type == "products"
        assert len(r.products) == 1
        assert r.products[0].image_url is not None

    def test_image_url_null_accepted(self):
        """`image_url=null` mora proći — legacy/missing slike (rag.py:419)."""
        r = assistant_response_adapter.validate_python({
            "type": "products",
            "text": "Evo proizvoda bez slika.",
            "products": [{
                "sifra": "G1", "name": "X", "price_km": 100,
                "availability": "Na lageru", "url": "https://x", "image_url": None,
            }],
        })
        assert isinstance(r, ProductsResponse)
        assert r.products[0].image_url is None

    def test_empty_products_list_rejected(self):
        """Pretraga sa 0 rezultata MORA koristiti EmptyResponse, ne products[]."""
        with pytest.raises(ValidationError) as exc_info:
            assistant_response_adapter.validate_python({
                "type": "products",
                "text": "Trebalo bi imati barem 1.",
                "products": [],
            })
        assert "at least 1" in str(exc_info.value).lower() or "min_length" in str(exc_info.value).lower()

    def test_missing_required_product_field_rejected(self):
        """Proizvod bez `price_km` ne prolazi."""
        with pytest.raises(ValidationError) as exc_info:
            assistant_response_adapter.validate_python({
                "type": "products",
                "text": "...",
                "products": [{
                    "sifra": "G1", "name": "X",
                    "availability": "Na lageru", "url": "https://x", "image_url": None,
                }],
            })
        assert "price_km" in str(exc_info.value)

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            assistant_response_adapter.validate_python({
                "type": "products",
                "text": "...",
                "products": [{
                    "sifra": "G1", "name": "X", "price_km": -1,
                    "availability": "Na lageru", "url": "https://x", "image_url": None,
                }],
            })

    def test_price_int_coerced_to_float(self):
        """Cijena kao integer se prihvata (Pydantic coerce)."""
        r = assistant_response_adapter.validate_python({
            "type": "products",
            "text": "...",
            "products": [{
                "sifra": "G1", "name": "X", "price_km": 929,
                "availability": "Na lageru", "url": "https://x", "image_url": None,
            }],
        })
        assert isinstance(r, ProductsResponse)
        assert isinstance(r.products[0].price_km, float)
        assert r.products[0].price_km == 929.0


class TestEmptyResponse:
    def test_valid_empty_passes(self):
        r = assistant_response_adapter.validate_python({
            "type": "empty",
            "message": "Nema laptopa pod tim uslovima u našem katalogu.",
        })
        assert isinstance(r, EmptyResponse)
        assert "Nema" in r.message

    def test_empty_message_string_rejected(self):
        with pytest.raises(ValidationError):
            assistant_response_adapter.validate_python({
                "type": "empty",
                "message": "",
            })


class TestMessageResponse:
    def test_valid_message_passes(self):
        r = assistant_response_adapter.validate_python({
            "type": "message",
            "content": "Pozdrav! Kako mogu pomoći?",
        })
        assert isinstance(r, MessageResponse)

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            assistant_response_adapter.validate_python({
                "type": "message",
                "content": "",
            })


class TestDiscriminator:
    def test_unknown_type_rejected(self):
        """Discriminator hvati pogrešan tip umjesto silent fallback."""
        with pytest.raises(ValidationError) as exc_info:
            assistant_response_adapter.validate_python({
                "type": "products_with_typo",
                "text": "...",
                "products": [],
            })
        assert "type" in str(exc_info.value).lower()

    def test_missing_type_rejected(self):
        with pytest.raises(ValidationError):
            assistant_response_adapter.validate_python({
                "text": "...",
                "products": [],
            })

    def test_validate_json_works(self):
        """JSON string ulaz (kako će dolaziti iz AI output-a) se direktno validira."""
        json_str = '{"type":"message","content":"Pozdrav!"}'
        r = assistant_response_adapter.validate_json(json_str)
        assert isinstance(r, MessageResponse)


class TestJsonSchemaExport:
    def test_schema_export_includes_all_types(self):
        """`json_schema()` mora opisati sva tri tipa za eksterne konzumente."""
        schema = assistant_response_adapter.json_schema()
        defs = schema.get("$defs", {}) or schema.get("definitions", {})
        names = set(defs.keys())
        assert {"ProductsResponse", "EmptyResponse", "MessageResponse"}.issubset(names)
