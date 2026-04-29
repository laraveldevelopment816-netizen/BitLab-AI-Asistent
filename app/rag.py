"""
Hibridna pretraga: BM25 (keyword) + vektor (cosine) sa score fusion 0.4/0.6.
Indeks se učitava jednom pri startu; model se inicijalizuje na prvom upitu.
"""
from __future__ import annotations

import json
import re
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from .config import settings

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text) if len(w) > 1]


def _norm01(arr: np.ndarray) -> np.ndarray:
    lo, hi = float(arr.min()), float(arr.max())
    if hi - lo < 1e-9:
        return np.zeros_like(arr)
    return (arr - lo) / (hi - lo)


class ProductIndex:
    def __init__(self) -> None:
        data = np.load(settings.products_index)
        self.embeddings: np.ndarray = data["embeddings"]   # [N, 384] float32
        self.ids: np.ndarray = data["ids"]                 # [N] int64

        meta_doc = json.loads(settings.products_meta.read_text(encoding="utf-8"))
        self._products: dict[str, Any] = meta_doc["products"]  # str(id) → meta

        # sifra → meta (za check_availability)
        self.sifra_map: dict[str, Any] = {
            m["sifra"]: m
            for m in self._products.values()
            if m.get("sifra")
        }

        corpus = [
            _tokenize(self._products[str(int(pid))].get("search_text", ""))
            for pid in self.ids
        ]
        self.bm25 = BM25Okapi(corpus)
        self._model: SentenceTransformer | None = None

    def preload_model(self) -> None:
        """Pozovi pri startu da bi prvi upit bio brz."""
        if self._model is None:
            self._model = SentenceTransformer(settings.embed_model)

    def _embed(self, text: str) -> np.ndarray:
        if self._model is None:
            self._model = SentenceTransformer(settings.embed_model)
        return self._model.encode(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0].astype(np.float32)

    def search(
        self,
        query: str,
        top_k: int = 5,
        max_price_km: float | None = None,
    ) -> list[dict[str, Any]]:
        q_vec = self._embed(query)
        vec_scores = self.embeddings @ q_vec             # dot product (embeddings su normirani)
        bm25_raw = np.array(self.bm25.get_scores(_tokenize(query)), dtype=np.float32)

        fused = 0.6 * _norm01(vec_scores) + 0.4 * _norm01(bm25_raw)
        ranked = np.argsort(-fused)

        # Prikupi buffer kandidata (4× top_k) da re-sort ne osiromasi rezultate
        candidates: list[tuple[dict[str, Any], float]] = []
        for idx in ranked:
            if len(candidates) >= top_k * 4:
                break
            pid = str(int(self.ids[idx]))
            meta = self._products.get(pid)
            if not meta:
                continue
            if max_price_km is not None:
                price = meta.get("price_km")
                if price is not None and float(price) > max_price_km:
                    continue
            candidates.append((meta, float(fused[idx])))

        # Artikli na stanju dolaze prvi; unutar grupe zadržava se redosljed relevantnosti
        candidates.sort(key=lambda x: (0 if (x[0].get("kolicina") or 0) > 0 else 1, -x[1]))

        results: list[dict[str, Any]] = []
        for meta, _ in candidates[:top_k]:
            url_raw = meta.get("url", "")
            if "/proizvod/" in url_raw:
                slug = url_raw.split("/proizvod/", 1)[1]
                url = f"https://webshop.bitlab.rs/{slug}.html"
            else:
                url = url_raw or None
            cover = meta.get("cover") or ""
            image_url = (
                f"https://webshop.bitlab.rs/files/products/img/{cover}"
                if cover else None
            )
            results.append({
                "sifra": meta.get("sifra", ""),
                "name": meta.get("name", ""),
                "price_km": meta.get("price_km"),
                "availability": meta.get("availability_label", "Provjeri dostupnost"),
                "kolicina": meta.get("kolicina", 0),
                "url": url,
                "image_url": image_url,
            })

        return results


_index: ProductIndex | None = None


def get_index() -> ProductIndex:
    global _index
    if _index is None:
        _index = ProductIndex()
    return _index
