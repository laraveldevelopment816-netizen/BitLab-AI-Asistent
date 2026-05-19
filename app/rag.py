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
_BRAND_PATH = settings.data_dir / "brend.json"
_MISSING_IMAGES_PATH = settings.data_dir / "missing_images.json"


def _load_missing_image_sifras() -> frozenset[str]:
    """Učitaj listu sifri proizvoda čije cover slike vraćaju 302 redirect
    na webshop homepage (= slika ne postoji na CDN-u, vidi
    scripts/audit_missing_images.py). Bez ovog filtera, browser pokušava
    učitati sliku, dobije HTML, sakrije <img> kroz onerror — ali Claude
    svejedno generiše ![](url) markup koji izgleda neuredno u raw output-u
    pa je bolje da image_url bude None od starta."""
    if not _MISSING_IMAGES_PATH.exists():
        return frozenset()
    try:
        data = json.loads(_MISSING_IMAGES_PATH.read_text(encoding="utf-8"))
        return frozenset(m["sifra"] for m in data.get("missing", []) if m.get("sifra"))
    except Exception:
        return frozenset()


_MISSING_IMAGE_SIFRAS = _load_missing_image_sifras()


def _load_category_terms() -> dict[str, list[str]]:
    if not _CATEGORY_TERMS_PATH.exists():
        return {}
    raw = json.loads(_CATEGORY_TERMS_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in raw.items() if not k.startswith("_") and isinstance(v, list)}


def _load_brands() -> list[dict[str, Any]]:
    """Učitaj brendove iz phpMyAdmin export-a (data/brend.json). Vraća listu
    {id, name, priority}. `priority` je 1–20 za top brendove (nullable)."""
    if not _BRAND_PATH.exists():
        return []
    raw = json.loads(_BRAND_PATH.read_text(encoding="utf-8"))
    for entry in raw:
        if entry.get("type") == "table" and entry.get("name") == "brend":
            data = entry.get("data", [])
            out: list[dict[str, Any]] = []
            for row in data:
                bid = (row.get("id") or "").strip()
                name = (row.get("name") or "").strip()
                if not bid or not name:
                    continue
                pri_raw = row.get("priority")
                priority = int(pri_raw) if pri_raw and pri_raw != "NULL" else None
                out.append({"id": bid, "name": name, "priority": priority})
            return out
    return []


# Generičke riječi koje se podudaraju sa imenom brenda ali NISU brand mention
# u upitu — npr. "max" je dio "MAX PRINT", ali "max" u "max budget" nije brand.
# Multi-token brendovi (COOLER MASTER, MAX PRINT, WESTERN DIGITAL, EZ COOL,
# LIPA MILL, LC-POWER) zahtijevaju puno ime ili karakteristični prvi token —
# ne damo da "cooler", "max", "western", "lipa" same triggeruju brand boost.
_BRAND_FIRST_TOKEN_BLOCKLIST = frozenset({
    "cooler", "western", "lipa", "max", "ez", "lc", "team",
    "g", "sapphire",
})


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
    prefix-match u OBA smjera. Pokriva BCS fleksije bez pravog stemmera:
    - Term je prefix tokena (laptop→laptopa, laptop→laptopovi).
    - Token je prefix terma (monitor→monitori, miš→miševi, zvuk→zvučnik).
    Drugi smjer je važan za singular query nasuprot plural CSV terma —
    SEO meta_keywords je obično u množini ("monitori", "tastature"), a
    korisnici tipkuju u jednini ("monitor 27\\""). Bez ovoga, head-noun
    "monitor" ne match-uje term "monitori".
    """
    if token in term_keys:
        return term_keys[token]
    for term, cats in term_keys.items():
        if " " in term:
            continue  # bigram terms riješavaju se zasebno
        if len(term) < 4 or len(token) < 4:
            continue
        # Smjer 1: term ⊆ token (laptop ⊆ laptopa)
        if token.startswith(term) and len(token) - len(term) <= 5:
            return cats
        # Smjer 2: token ⊆ term (monitor ⊆ monitori) — len_diff ≤ 3 jer BCS
        # plural sufiksi su kratki (i, e, ovi, ima); veći delta vodi false
        # positive (npr. "tab" ⊆ "tablete" 4-char delta nije isti tip).
        if term.startswith(token) and len(term) - len(token) <= 3:
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

        # Pripremi brand lookup-e
        self._brands = _load_brands()
        # id_brend → priority (None ako brend nema priority)
        self._brand_priority: dict[str, int | None] = {
            b["id"]: b["priority"] for b in self._brands
        }
        # brand_key (lowercased, no-diacritics) → id_brend
        # Singleword brendovi: cijelo ime kao key. Multi-word brendovi: dodaj
        # i pun višetokeni key (npr. "cooler master") + provjeravaj kao bigram
        # u query-ju (single token "cooler" sam za sebe nije dovoljan — vidi
        # _BRAND_FIRST_TOKEN_BLOCKLIST).
        self._brand_key_to_id: dict[str, str] = {}
        for b in self._brands:
            name = b["name"]
            if not name or name.lower() == "ostalo":
                continue
            key = _strip_diacritics(name.lower()).strip()
            self._brand_key_to_id[key] = b["id"]
            tokens = key.split()
            # Single-token brendovi (apple, asus, hp, lg, dji…)
            if len(tokens) == 1:
                continue
            # Multi-token brendovi: omogući i prvi token kao key — ali samo ako
            # prvi token NIJE generička riječ (cooler, western, max…).
            if tokens[0] not in _BRAND_FIRST_TOKEN_BLOCKLIST:
                self._brand_key_to_id.setdefault(tokens[0], b["id"])
        # idx → id_brend (za brzi brand lookup po vektorskoj poziciji)
        self._idx_to_brand: list[str] = [
            (self._products.get(str(int(pid)), {}).get("id_brend") or "").strip()
            for pid in self.ids
        ]

    def preload_model(self) -> None:
        """Pozovi pri startu da bi prvi upit bio brz. Skupo na WSL2 (~50s).

        device="cpu" eksplicitno — bez toga torch novije verzije ide preko
        "meta tensor" lazy loading-a, pa kasniji `.to(device)` baca
        NotImplementedError ("Cannot copy out of meta tensor"). Bug iz
        TEST-failures-pwr-migration.md §3."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(settings.embed_model, device="cpu")

    def _embed(self, text: str) -> np.ndarray:
        if self._model is None:
            self.preload_model()
        return self._model.encode(
            [text],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )[0].astype(np.float32)

    def _detect_intent_brands(self, query: str) -> set[str]:
        """Vrati set id_brend-ova koje query implicira preko brand imena.

        Strategija:
        - Tokenizuj query (sa diacritic strip).
        - Provjeri svaki token: ako se točno poklapa sa brand_key, dodaj id.
        - Provjeri bigrame: "cooler master", "western digital", "max print".
        - Multi-word brendovi (cooler master) zahtijevaju puni bigram match —
          single token "cooler" je u blocklisti jer bi blokirao "cpu cooler"
          search false-positive.
        """
        q_norm = _strip_diacritics(query.lower())
        tokens = _tokenize(q_norm)
        if not tokens:
            return set()
        hits: set[str] = set()
        # Direct token match (apple, asus, hp, lg…)
        for tok in tokens:
            bid = self._brand_key_to_id.get(tok)
            if bid:
                hits.add(bid)
        # Bigram match (cooler master, western digital…)
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            bid = self._brand_key_to_id.get(bigram)
            if bid:
                hits.add(bid)
        return hits

    def _detect_intent_categories(self, query: str) -> set[str]:
        """Vrati cat_ids koje query implicira preko `category_terms.json`.

        Heuristika (Opus high-effort design):
        - Filtrira BCS stop-riječi prije brojanja.
        - Aktivno za upite sa ≤4 NON-STOP tokena ("najbolji laptop do 1500 KM"
          → ["laptop", "1500"] = 2 non-stop, prošlo).
        - **Head-noun pravilo sa fallback-om**: prvi non-stop token koji
          match-uje term je head. "miš za laptop" → head je "miš" (prvi).
          "gaming miš" → first="gaming" (modifier, no match), fallback na
          "miš" → cat 277. "samsung tv" → first="samsung" (brand, filtriran
          iz term_keys), fallback na "tv" → cat 163.
        - Bidirektioni prefix-match za BCS fleksiju (laptop↔laptopa,
          monitor↔monitori).
        """
        q_norm = _strip_diacritics(query.lower())
        all_tokens = _tokenize(q_norm)
        non_stop = [t for t in all_tokens if t not in _BCS_STOP_WORDS]
        if not non_stop or len(non_stop) > 4:
            return set()

        # Head-noun fallback: probaj prvi koji match-uje. Ako prvi ne match-uje
        # (modifier kao "gaming", brand kao "samsung"), pomjeri se dalje.
        # Prestajemo na prvom match-u da izbjegnemo "miš za laptop" → laptop.
        hits: set[str] = set()
        for tok in non_stop:
            head_hits = _is_term_match(tok, self._term_to_cats)
            if head_hits:
                hits |= head_hits
                break

        # Bigram check: prvi + drugi non-stop token kao multi-word term
        # ("matična ploča", "fiksni telefon", "gift card"). Ne ograničavamo
        # na prvi par — provjerimo sve uzastopne parove jer "samsung galaxy
        # s24" head je "galaxy" tek na poziciji 2.
        for i in range(len(non_stop) - 1):
            bigram = f"{non_stop[i]} {non_stop[i+1]}"
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
        category_id: str | None = None,
        brand_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Hibridna pretraga sa opcionim hard filter-ima.

        - `category_id` (od Claude-a) — hard filter na `categories_id`,
          drastično smanjuje accessory šum.
        - `brand_id` (od Claude-a) — hard filter na `id_brend`. Korisno za
          "Apple iPhone" tipa upite gdje korisnik eksplicitno traži brend.
        - Bez hard filtera, intent-detekcija detektuje kategoriju I brend
          iz query-ja i primijenjuje soft boost (kumulativno do +0.5 ako
          oba match-uju)."""
        q_vec = self._embed(query)
        vec_scores = self.embeddings @ q_vec             # dot product (embeddings su normirani)
        bm25_raw = np.array(self.bm25.get_scores(_tokenize(query)), dtype=np.float32)

        fused = 0.6 * _norm01(vec_scores) + 0.4 * _norm01(bm25_raw)

        # Soft boost-ovi se primjenjuju samo kad AI nije dao hard filter.
        # Cilj: katchup za "near miss" gdje AI ne pošalje filter, ali query
        # implicira kategoriju ili brend. Boost je kumulativan (+0.25 cat,
        # +0.25 brand), max +0.5.
        if category_id is None:
            intent_cats = self._detect_intent_categories(query)
            if intent_cats:
                boost = np.zeros_like(fused)
                for i, cat in enumerate(self._idx_to_cat):
                    if cat in intent_cats:
                        boost[i] = 0.25
                fused = fused + boost

        if brand_id is None:
            intent_brands = self._detect_intent_brands(query)
            if intent_brands:
                brand_boost = np.zeros_like(fused)
                for i, bid in enumerate(self._idx_to_brand):
                    if bid in intent_brands:
                        brand_boost[i] = 0.25
                fused = fused + brand_boost

        ranked = np.argsort(-fused)

        # Prikupi buffer kandidata. Hard filter čisti puno → veći buffer.
        buffer_mult = 8 if (category_id or brand_id) else 4
        candidates: list[tuple[dict[str, Any], float]] = []
        for idx in ranked:
            if len(candidates) >= top_k * buffer_mult:
                break
            pid = str(int(self.ids[idx]))
            meta = self._products.get(pid)
            if not meta:
                continue
            if category_id is not None:
                if (meta.get("categories_id") or "").strip() != category_id:
                    continue
            if brand_id is not None:
                if (meta.get("id_brend") or "").strip() != brand_id:
                    continue
            if max_price_km is not None:
                price = meta.get("price_km")
                if price is not None and float(price) > max_price_km:
                    continue
            candidates.append((meta, float(fused[idx])))

        # Sort: na lageru prvi, zatim po relevantnosti. Brand priority je
        # tie-breaker UNUTAR iste relevance grupe — kad search ne razlučuje
        # između dva blizu-skor proizvoda, top-priority brand (Apple, ASUS,
        # HP) ide prvi. Granularnost: zaokruži score na 2 decimale prije
        # poređenja, da brand priority pobijedi samo kad je razlika minorna.
        def _sort_key(item: tuple[dict[str, Any], float]) -> tuple:
            meta, score = item
            in_stock = 0 if (meta.get("kolicina") or 0) > 0 else 1
            score_bucket = round(score, 2)  # group near-equal scores
            bid = (meta.get("id_brend") or "").strip()
            pri = self._brand_priority.get(bid)
            # priority 1 = najtraženiji; None = ne ulazi u tie-break (rang 99)
            priority_rank = pri if pri is not None else 99
            return (in_stock, -score_bucket, priority_rank, -score)

        candidates.sort(key=_sort_key)

        results: list[dict[str, Any]] = []
        for meta, _ in candidates[:top_k]:
            url_raw = meta.get("url", "")
            if "/proizvod/" in url_raw:
                slug = url_raw.split("/proizvod/", 1)[1]
                url = f"https://webshop.bitlab.rs/{slug}.html"
            else:
                url = url_raw or None
            cover = meta.get("cover") or ""
            sifra = meta.get("sifra", "")
            # Legacy webshop naming: dugi cover prefix (≥7 cifara) je novi
            # storage; kratki legacy prefix (`728_lenovo.jpg`, `45_x.jpg`)
            # su iz starog sistema gdje fajlovi nisu migrirani — server
            # vraća 302 na homepage. Plus eksplicitan list missing sifri
            # iz audit-a. Oba uslova → image_url = None.
            cover_is_legacy = bool(cover) and not re.match(r'^\d{7,}_', cover)
            cover_is_known_missing = sifra in _MISSING_IMAGE_SIFRAS
            if not cover or cover_is_legacy or cover_is_known_missing:
                image_url = None
            else:
                image_url = f"https://webshop.bitlab.rs/files/products/img/{cover}"
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
