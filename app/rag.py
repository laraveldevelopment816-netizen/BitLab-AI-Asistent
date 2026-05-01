"""
Hibridna pretraga: BM25 (keyword) + vektor (cosine) sa score fusion 0.4/0.6.
Plus search-time category boost za kratke generičke upite ("laptop", "tv") —
embedding sam ne razlučuje pravi laptop od torbe za laptop jer torba ima višu
density "laptop" tokena u kratkom imenu.

Indeks se učitava jednom pri startu; model se inicijalizuje na prvom upitu.
"""
from __future__ import annotations

import json
import re
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from .config import settings

# sentence_transformers se lazy-importuje u _embed/preload_model — povlači
# torch + transformers (~50s na WSL2 /mnt/c). Bez ovoga startup je nepodnošljiv.

_CATEGORY_TERMS_PATH = settings.data_dir / "category_terms.json"


def _load_category_terms() -> dict[str, list[str]]:
    if not _CATEGORY_TERMS_PATH.exists():
        return {}
    raw = json.loads(_CATEGORY_TERMS_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_") and isinstance(v, list)}


def _strip_diacritics(s: str) -> str:
    """Č→c, š→s, ž→z, ć→c, đ→d — da match radi i ako korisnik ne piše dijakritike."""
    return (
        s.replace("č", "c").replace("ć", "c").replace("š", "s")
         .replace("ž", "z").replace("đ", "d")
         .replace("Č", "c").replace("Ć", "c").replace("Š", "s")
         .replace("Ž", "z").replace("Đ", "d")
    )


# BCS stop riječi koje korisnici dodaju u upit ali ne nose semantiku tipa proizvoda.
# Bez ovog filtera "najbolji laptop do 1500 KM" pada na 5 tokena pa boost ne radi.
_BCS_STOP_WORDS = frozenset({
    "za", "i", "ili", "u", "na", "do", "od", "iz", "sa", "sa", "po",
    "imam", "imate", "imas", "ima", "li", "je", "su", "da", "ne",
    "treba", "trebam", "trebamo", "treba", "hocu", "zelim", "zelio",
    "molim", "moze", "mozete", "moze", "kako", "sta", "koji", "koja",
    "koje", "koliko", "ko", "gdje", "kada", "zasto", "to", "ovo", "ono",
    "moj", "moja", "moje", "vas", "vasa", "vase", "ja", "mi", "ti", "vi",
    "the", "a", "an", "is", "are", "what", "where", "which",
    "km", "bam", "eur", "evra", "eura",
    "najbolji", "najbolja", "najbolje", "dobar", "dobra", "dobro",
    "novi", "nova", "novo", "stari", "stara", "staro",
})


def _is_term_match(token: str, term_keys: dict[str, set[str]]) -> set[str]:
    """Vrati cat_ids ako se token poklapa sa nekim term-om — direktno ili
    prefix-match (laptopa→laptop, laptopovi→laptop). Pokriva BCS fleksije
    bez pravog stemmera."""
    # Direct hit
    if token in term_keys:
        return term_keys[token]
    # Prefix-match: term je prefix tokena i token je do 5 char duži
    # (npr. "laptopa", "laptopovi", "tvovi") — sprečava "laptopdjenotebookgore"
    for term, cats in term_keys.items():
        if " " in term:
            continue  # bigram terms riješavaju se zasebno
        if len(term) >= 4 and token.startswith(term) and len(token) - len(term) <= 5:
            return cats
    return set()

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
        self._model: Any | None = None

        # Pripremi category boost lookup-e
        self._category_terms = _load_category_terms()
        # term (lowercase, no-diacritics) → set of cat_ids koje term aktivira
        self._term_to_cats: dict[str, set[str]] = {}
        for cat_id, terms in self._category_terms.items():
            for t in terms:
                key = _strip_diacritics(t.lower()).strip()
                if not key:
                    continue
                self._term_to_cats.setdefault(key, set()).add(cat_id)
        # idx → cat_id (za brzi cat lookup po vektorskoj poziciji)
        self._idx_to_cat: list[str] = [
            (self._products.get(str(int(pid)), {}).get("categories_id") or "").strip()
            for pid in self.ids
        ]

    def preload_model(self) -> None:
        """Pozovi pri startu da bi prvi upit bio brz. Skupo na WSL2 (~50s)."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(settings.embed_model)

    def _embed(self, text: str) -> np.ndarray:
        if self._model is None:
            self.preload_model()
        return self._model.encode(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0].astype(np.float32)

    def _detect_intent_categories(self, query: str) -> set[str]:
        """Vrati cat_ids koje query implicira preko `category_terms.json`.

        Heuristika (Opus high-effort design):
        - Filtrira BCS stop-riječi prije brojanja.
        - Aktivno za upite sa ≤4 NON-STOP tokena ("najbolji laptop do 1500 KM"
          → ["laptop", "1500"] = 2 non-stop, prošlo).
        - **Boost samo ako prvi non-stop token match-uje term.** Ovo riješava
          "mis za laptop" — head noun je "miš", ne "laptop"; ne smijemo gurnuti
          laptopove iznad miševa.
        - Prefix-match za BCS fleksiju ("laptopa", "laptopovi" → laptop).
        """
        q_norm = _strip_diacritics(query.lower())
        all_tokens = _tokenize(q_norm)
        non_stop = [t for t in all_tokens if t not in _BCS_STOP_WORDS]
        if not non_stop or len(non_stop) > 4:
            return set()

        # Pravilo head-noun: provjeri samo prvi non-stop token.
        first = non_stop[0]
        hits = _is_term_match(first, self._term_to_cats)

        # Bigram check: ako prvi + drugi non-stop token formiraju multi-word term
        # ("matična ploča", "fiksni telefon", "gift card")
        if len(non_stop) >= 2:
            bigram = first + " " + non_stop[1]
            if bigram in self._term_to_cats:
                hits |= self._term_to_cats[bigram]

        # Multi-word substring match (npr. "prijenosni racunar" u dužem query-ju)
        for term_key, cats in self._term_to_cats.items():
            if " " in term_key and term_key in q_norm:
                hits |= cats

        return hits

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

        # Category boost — pomjeri proizvode iz match-ed kategorija u top.
        # Bonus 0.25 (na 0-1 skali) je dovoljno da nadjača density tokena u
        # accessory imenima ("Torba za notebook ... Laptop") ali ne toliko
        # da preuzme rezultate od relevantnih konkurenata u istoj kategoriji.
        intent_cats = self._detect_intent_categories(query)
        if intent_cats:
            boost = np.zeros_like(fused)
            for i, cat in enumerate(self._idx_to_cat):
                if cat in intent_cats:
                    boost[i] = 0.25
            fused = fused + boost

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
