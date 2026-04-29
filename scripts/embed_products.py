"""
Jednokratna skripta — generiše embedding indeks za BitLab katalog.

Pokreće se LOKALNO (van Claude Code sesije, da ne troši sesijske tokene):

    source .venv/bin/activate
    python scripts/embed_products.py

Ulaz:
    data/all-products.json      (phpMyAdmin export)

Izlaz:
    data/products.index.npz     (embeddings: float32 [N, 384] + ids: int64 [N])
    data/products.meta.json     (display metadata + BM25 corpus, po id-u)

Prvi put traje ~3–5 minuta na CPU-u (skida ~120MB sentence-transformer model).
Naredni put ~1–2 minuta.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

# Bootstrap path da skripta radi i iz korijena i iz /scripts
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = _HTML_TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any, default: int = 0) -> int:
    if v is None or v == "":
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def parse_products(raw_path: Path) -> list[dict[str, Any]]:
    """Iz phpMyAdmin export-a izvuče redove iz tabele 'products'."""
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    for entry in data:
        if entry.get("type") == "table" and entry.get("name") == "products":
            return entry.get("data", [])
    raise ValueError(f"Tabela 'products' nije pronađena u {raw_path}")


def availability_label(product: dict[str, Any]) -> str:
    kolicina = _to_int(product.get("kolicina"))
    dobavljivost = (product.get("dobavljivost") or "").strip()
    if kolicina > 0:
        return f"Na lageru ({kolicina} kom)"
    if dobavljivost == "1":
        return "Dobavljivo po narudžbi"
    return "Provjeri dostupnost"


def build_search_text(p: dict[str, Any]) -> str:
    """Tekst koji ide u embedding (i u BM25 korpus)."""
    parts = [
        _clean(p.get("name")),
        _clean(p.get("description")),
        _clean(p.get("description_full")),
        _clean(p.get("keywords")),
    ]
    text = ". ".join(part for part in parts if part)
    return text[:1000]  # cap da batch ostaje brz


def build_product_meta(p: dict[str, Any]) -> dict[str, Any]:
    urlhash = (p.get("urlhash") or "").strip()
    url = settings.product_url_template.format(urlhash=urlhash) if urlhash else None

    return {
        "id": _to_int(p.get("id")),
        "sifra": (p.get("sifra") or "").strip(),
        "name": _clean(p.get("name")),
        "price_km": _to_float(p.get("price")),
        "price_old_km": _to_float(p.get("price_old")),
        "kolicina": _to_int(p.get("kolicina")),
        "availability_label": availability_label(p),
        "categories_id": (p.get("categories_id") or "").strip() or None,
        "id_brend": (p.get("id_brend") or "").strip() or None,
        "ean": (p.get("ean") or "").strip() or None,
        "cover": (p.get("cover") or "").strip() or None,
        "url": url,
        "search_text": build_search_text(p),  # za BM25 + debug
    }


def main() -> None:
    raw_path = settings.products_json
    if not raw_path.exists():
        print(f"GREŠKA: {raw_path} ne postoji.", file=sys.stderr)
        sys.exit(1)

    print(f"→ Učitavam proizvode iz {raw_path}")
    raw_products = parse_products(raw_path)
    print(f"  Pronađeno {len(raw_products)} redova u tabeli 'products'.")

    # Filter: vidljivi + ima ime
    products = [
        p for p in raw_products
        if p.get("visible") == "true" and _clean(p.get("name"))
    ]
    print(f"  Filtrirano (visible=true, ima ime): {len(products)} proizvoda.")

    if not products:
        print("GREŠKA: nema proizvoda za indeksiranje.", file=sys.stderr)
        sys.exit(2)

    print(f"→ Učitavam embedding model: {settings.embed_model}")
    print("  (prvi put se skida ~120MB — sačekaj.)")
    model = SentenceTransformer(settings.embed_model)

    # Provjeri da je dim u config-u tačan
    actual_dim = model.get_sentence_embedding_dimension()
    if actual_dim != settings.embed_dim:
        print(
            f"  UPOZORENJE: embed_dim={settings.embed_dim} u config-u, "
            f"a model vraća {actual_dim}. Ažuriraj config.",
            file=sys.stderr,
        )

    metas = [build_product_meta(p) for p in products]
    texts = [m["search_text"] for m in metas]
    ids = np.array([m["id"] for m in metas], dtype=np.int64)

    print(f"→ Generišem embeddinge za {len(texts)} stavki ...")
    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,  # cosine = dot product
        convert_to_numpy=True,
    ).astype(np.float32)

    print(f"  Embeddings shape: {embeddings.shape}, dtype: {embeddings.dtype}")

    settings.data_dir.mkdir(parents=True, exist_ok=True)

    np.savez_compressed(
        settings.products_index,
        embeddings=embeddings,
        ids=ids,
    )
    print(f"✓ Sačuvano: {settings.products_index} "
          f"({settings.products_index.stat().st_size / 1_048_576:.1f} MB)")

    meta_doc = {
        "embed_model": settings.embed_model,
        "embed_dim": int(embeddings.shape[1]),
        "count": len(metas),
        "products": {str(m["id"]): m for m in metas},
    }
    settings.products_meta.write_text(
        json.dumps(meta_doc, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✓ Sačuvano: {settings.products_meta} "
          f"({settings.products_meta.stat().st_size / 1_048_576:.1f} MB)")
    print("\nGotovo. Sad možeš pokrenuti uvicorn:")
    print("    uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
