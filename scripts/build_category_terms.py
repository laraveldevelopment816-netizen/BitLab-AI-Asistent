"""
Generiše data/category_terms.json iz data/categories.csv.

Source of truth: phpMyAdmin export tabele `categories` u CSV-u (255 redova,
~238 vidljivih). Iz svakog reda izvlačimo BCS termine koje korisnici tipkuju
kad traže tu kategoriju proizvoda — primarno iz polja `meta_keywords`
(SEO-curirano) plus `name` kao fallback.

Termini se filtriraju kroz:
- STOP_TERMS lista — SEO šum ("BiH", "online", "kupite", "povoljno"...)
- Brand-only single tokens (npr. "Apple", "HP") — tih treba klasifikovati kao
  brend, ne kao kategoriju (vidi rag.py brand detection)
- Multi-word > 3 riječi — preverbozno za head-noun match

Pokreni: python scripts/build_category_terms.py

Bez reindex-a, search-time category boost u rag.py odmah radi šire.
Za maksimalnu pobjedu (boost u embeddingu/BM25) potrebno je nakon ovog
pokrenuti `python scripts/embed_products.py` jer embed_products.py prefiksira
search_text sa kategorijskim terminima 3x.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "categories.csv"
BRAND_PATH = PROJECT_ROOT / "data" / "brend.json"
PRODUCTS_META_PATH = PROJECT_ROOT / "data" / "products.meta.json"
OUT_PATH = PROJECT_ROOT / "data" / "category_terms.json"


# Termini koji NE treba da budu kategorijski boost — SEO šum, lokacijski sufiksi.
# Razdvojeno na: STOP_PHRASES (drop term ako je tačno ovo), STOP_SUBSTRINGS
# (drop term ako sadrži substring), STOP_SUFFIXES (drop term ako se završava sa).
STOP_PHRASES = frozenset({
    "bih", "rs", "online", "shop", "webshop",
    "kupite", "kupi", "kupiti", "prodaja", "kupovina",
    "povoljno", "povoljna", "povoljni", "povoljne", "povoljnih",
    "novo", "novi", "nova", "popusti", "akcija",
    "katalog", "ponuda", "cijena", "cijene", "cijenama",
    "klase",  # "A++ klase" leftover
})

STOP_SUBSTRINGS = frozenset({
    "bitlab", "kupite online", "kupiti online", "po povoljnoj cijeni",
})

# Sufiksi koji obilježavaju verbozne SEO termine ("povoljni laptopi BiH",
# "kupiti laptop online") — odsijecamo ih da bismo izolirali head-noun.
TRAILING_NOISE_TOKENS = frozenset({
    "bih", "rs", "online", "shop", "webshop",
    "povoljno", "povoljna", "povoljni", "povoljne", "povoljnih",
    "kupite", "kupi", "kupiti",
    "klase",
})

LEADING_NOISE_TOKENS = frozenset({
    "kupite", "kupi", "kupiti",
    "povoljno", "povoljna", "povoljni", "povoljne", "povoljnih",
    "novi", "nova", "novo",
})


_WORD_RE = re.compile(r"[A-Za-zČĆŠŽĐčćšžđ0-9.]+", re.UNICODE)


# Termini koji se DODAJU CSV-extracted listi za određene kategorije. Pokriva
# tri tipa rupa: (1) BCS skraćenice/kolokvijalizmi koje SEO meta_keywords ne
# uključuju ("tv" alone, "mb" za matičnu, "kompjuter"), (2) singular forme
# kad CSV ima samo plural ("kamera" gdje CSV ima "kamere"), (3) migration
# drift gdje cat ima 500+ proizvoda ali CSV row je promijenjen ili obrisan
# (cat 277 "Ostalo" stvarno sadrži miševe).
#
# Drži OVDJE — single source of truth. Ako brand name završi ovde, izolovan
# (npr. "iphone" → cat 175), to je OK jer iPhone je product line, ne brand.
MANUAL_TERM_ADDITIONS: dict[str, list[str]] = {
    # Računari — kompjuter, pc kao colloquial
    "17": ["kompjuter", "pc", "stoni racunar"],
    # Laptopi — singular i prijenosni varianti
    "98": ["prijenosno", "prijenosni"],
    # Matične ploče — common abbreviations + singular forms
    "108": ["maticna", "maticna ploca", "mb", "mainboard"],
    # Televizori — kratko "tv" + singular
    "163": ["tv", "televizor"],
    # Mobiteli — singular varijanta
    "175": ["telefon", "smartfon"],
    # Tableti — singular
    "99": ["tablet"],
    # Monitori — singular
    "224": ["monitor"],
    # Tastature — singular + tipkovnica (HR varijanta često u Sarajevu)
    "220": ["tastatura", "tipkovnica"],
    # Cat 277 — migration drift: CSV ima "Ostalo" ali 535 proizvoda, 45%
    # miševi. AI pretraga za "miš" mora hitnuti ovu cat.
    "277": ["miš", "mis", "miševi"],
    # Cat 309 — router u BCS-u
    "309": ["router", "ruter"],
    # Cat 124 — laserski printer singular
    "124": ["printer", "stampac"],
    # Cat 137 — usb kabal singular
    "137": ["kabal", "kabel", "usb kabal"],
    # Cat 393 — gift kartice colloquialisms
    "393": ["voucher", "robux", "playstation kredit", "digitalni kredit"],
    # Cat 270 — switch generic
    "270": ["switch", "preklopnik"],
    # Cat 257 — usb stick colloquial
    "257": ["usb stik", "memorijski stik"],
    # Cat 202 — powerbank slang
    "202": ["powerbank", "eksterna baterija", "prenosivi punjac"],
    # Cat 304 — heftalica i ostali kancelarijski
    "304": ["heftalica", "alat", "lopta", "skalpel"],
    # Cat 314 — punjac singular
    "314": ["punjac", "auto punjac", "zidni punjac"],
    # Cat 220 — već imamo tastatura, dodaj gaming/wireless
    # (već u CSV terms vjerovatno) — ako nije, ovaj fallback dodaje
}


def _strip_diacritics(s: str) -> str:
    """Č→c, š→s, ž→z, ć→c, đ→d (lowercase form)."""
    return (
        s.replace("č", "c").replace("ć", "c").replace("š", "s")
         .replace("ž", "z").replace("đ", "d")
    )


def _load_brand_names() -> set[str]:
    """Učitaj set imena brendova (lowercase, bez dijakritike) — koristi se za
    filter brand-only single-token terma iz meta_keywords."""
    if not BRAND_PATH.exists():
        return set()
    data = json.loads(BRAND_PATH.read_text(encoding="utf-8"))
    brand_rows = []
    for entry in data:
        if entry.get("type") == "table" and entry.get("name") == "brend":
            brand_rows = entry.get("data", [])
            break
    names = set()
    for b in brand_rows:
        n = (b.get("name") or "").strip().lower()
        if not n or n == "ostalo":
            continue
        names.add(_strip_diacritics(n))
        # Multi-word brendovi: dodaj i prvi token (npr. "COOLER MASTER" → "cooler")
        first = n.split()[0]
        if first and len(first) >= 3:
            names.add(_strip_diacritics(first))
    return names


def _normalize_term(term: str) -> str | None:
    """Očisti pojedinačni term: lowercase, trim, odsijeci leading/trailing noise.
    Vraća None ako term ne preživi filter."""
    t = term.strip().lower()
    if not t:
        return None
    # Odsijeci leading/trailing noise tokens iterativno
    tokens = t.split()
    while tokens and tokens[0] in LEADING_NOISE_TOKENS:
        tokens.pop(0)
    while tokens and tokens[-1] in TRAILING_NOISE_TOKENS:
        tokens.pop()
    if not tokens:
        return None

    cleaned = " ".join(tokens)
    if cleaned in STOP_PHRASES:
        return None
    for sub in STOP_SUBSTRINGS:
        if sub in cleaned:
            return None
    # 1-char tokeni i prazni
    if len(cleaned) < 2:
        return None
    # Preverbozno (>3 tokena) — head-noun match neće raditi
    if len(tokens) > 3:
        return None
    # Drop ako sadrži samo brojeve/separatore
    if not _WORD_RE.search(cleaned):
        return None
    return cleaned


def _extract_terms_from_keywords(meta_keywords: str) -> list[str]:
    """meta_keywords je comma-separated — split, normalize, dedup, preserve order."""
    if not meta_keywords or meta_keywords == "NULL":
        return []
    parts = [p.strip() for p in meta_keywords.split(",")]
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        norm = _normalize_term(p)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def _extract_terms_from_name(name: str) -> list[str]:
    """name može biti "RAM memorija", "UPS, stabilizatori, ..." — split na
    common separatorima i normalizuj svaki dio."""
    if not name:
        return []
    # Split na zarez ili "/"
    parts = re.split(r"[,/]", name)
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        # Drop trailing "..." marker
        p = p.replace("...", "").strip()
        norm = _normalize_term(p)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def _filter_brand_only(terms: list[str], brand_names: set[str]) -> list[str]:
    """Drop single-word term koji se poklapa sa imenom brenda — ti termini
    pripadaju brand-detection sistemu, ne category-detection. Multi-word
    "HP printer", "Apple iPhone" zadržavamo."""
    out: list[str] = []
    for t in terms:
        tokens = t.split()
        if len(tokens) == 1 and _strip_diacritics(tokens[0]) in brand_names:
            continue
        out.append(t)
    return out


def _build_terms_for_row(
    row: dict[str, str],
    brand_names: set[str],
) -> list[str]:
    """Spoji termine iz meta_keywords (primarno) + name (fallback)."""
    seen: set[str] = set()
    out: list[str] = []

    # Primarno: meta_keywords (SEO-curirano)
    for t in _extract_terms_from_keywords(row.get("meta_keywords", "")):
        if t not in seen:
            seen.add(t)
            out.append(t)

    # Fallback: name (može da donese term koji nije u keywords)
    for t in _extract_terms_from_name(row.get("name", "")):
        if t not in seen:
            seen.add(t)
            out.append(t)

    # Filter brand-only single tokens
    out = _filter_brand_only(out, brand_names)
    return out


# Minimalni broj proizvoda da bi cat dobila boost. Nizak prag jača drift —
# CSV taxonomy je novija od products snapshot-a, pa cat može imati CSV row
# (sa "smart tv" u keywords) ali samo 1 stvarni proizvod jer su ostali
# još uvijek u staroj cat_id-i. Boost takvih cats znači da AI dobije malo
# rezultata. Threshold 5 odsijeca te ghost cats; ostavlja sve realno aktivne.
MIN_PRODUCTS_FOR_BOOST = 5


def _cat_id_product_counts() -> dict[str, int]:
    """Vrati mapu cat_id → broj proizvoda iz products.meta.json. Koristimo
    threshold da odbacimo migration ghost cats (CSV row postoji, ali svi
    proizvodi sa istim imenom stoje u staroj cat_id-i). Bez threshold-a,
    "samsung tv" boost-uje cat 148 (1 proizvod) umjesto cat 163 (67 TV-ova)."""
    if not PRODUCTS_META_PATH.exists():
        return {}
    data = json.loads(PRODUCTS_META_PATH.read_text(encoding="utf-8"))
    out: dict[str, int] = {}
    for p in data.get("products", {}).values():
        cid = (p.get("categories_id") or "").strip()
        if cid:
            out[cid] = out.get(cid, 0) + 1
    return out


def main() -> None:
    if not CSV_PATH.exists():
        print(f"GREŠKA: {CSV_PATH} ne postoji.", file=sys.stderr)
        sys.exit(1)

    brand_names = _load_brand_names()
    print(f"→ Učitano {len(brand_names)} brand imena za filter.")

    cat_counts = _cat_id_product_counts()
    eligible_cats = {cid for cid, c in cat_counts.items() if c >= MIN_PRODUCTS_FOR_BOOST}
    skipped_low = len(cat_counts) - len(eligible_cats)
    print(f"→ Cat_id-ova sa proizvodima: {len(cat_counts)}")
    print(f"  Eligibilnih (>= {MIN_PRODUCTS_FOR_BOOST} proizvoda): {len(eligible_cats)}")
    print(f"  Ispod praga (drift kandidati): {skipped_low}")

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"→ Pročitano {len(rows)} redova iz {CSV_PATH.name}.")

    out: dict[str, object] = {
        "_comment": (
            "Auto-generisano iz data/categories.csv pomoću "
            "scripts/build_category_terms.py — NE editovati ručno; izmjene "
            "prave u CSV-u (meta_keywords, name) i regenerisati. Mapiranje "
            "cat_id → BCS termini za search-time category boost u rag.py i "
            "embedding-time prefix u embed_products.py. Iskljuceni su cat-ovi "
            f"sa < {MIN_PRODUCTS_FOR_BOOST} proizvoda (migration ghost-ovi)."
        ),
    }

    csv_by_id = {(r.get("id") or "").strip(): r for r in rows if r.get("id")}

    # MANUAL_TERM_ADDITIONS može da pominje cat-ove koji nisu u eligible_cats
    # (npr. cat 277 ima 535 proizvoda — eligible — ali CSV row mu je "Ostalo"
    # status=0 što je OK; eligible filter pušta sve >=5 proizvoda bez obzira
    # na status). Bitno: MANUAL ide u out čak i ako CSV nema termin.
    relevant_cats = eligible_cats | set(MANUAL_TERM_ADDITIONS.keys())

    empty_count = 0
    no_csv_row = 0
    for cat_id in sorted(relevant_cats, key=lambda x: int(x) if x.isdigit() else 0):
        row = csv_by_id.get(cat_id)
        csv_terms: list[str] = []
        if row:
            csv_terms = _build_terms_for_row(row, brand_names)
        else:
            no_csv_row += 1

        # Manual additions: dedupliciraj sa CSV terminima, dodaj nove na kraj
        manual_extras = MANUAL_TERM_ADDITIONS.get(cat_id, [])
        seen = {t for t in csv_terms}
        merged = list(csv_terms)
        for t in manual_extras:
            t_norm = t.strip().lower()
            if t_norm and t_norm not in seen:
                seen.add(t_norm)
                merged.append(t_norm)

        if not merged:
            empty_count += 1
            continue
        out[cat_id] = merged

    OUT_PATH.write_text(
        json.dumps(out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    term_count = sum(len(v) for k, v in out.items() if not k.startswith("_"))
    cat_count = sum(1 for k in out if not k.startswith("_"))
    print(f"\n✅ {OUT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"   Kategorije sa terminima: {cat_count} (od {len(eligible_cats)} eligibilnih)")
    print(f"   Ukupno termina: {term_count}")
    print(f"   Bez termina (preskočeno): {empty_count}")
    if no_csv_row:
        print(f"   Cat ima proizvode ali nema reda u CSV-u: {no_csv_row}")
    print()
    print("Provjeri rezultate, pa po potrebi pokreni:")
    print("    python scripts/embed_products.py    # da prefix-i uđu u indeks (~5 min)")
    print("Ili odmah testiraj samo search-time boost:")
    print("    pytest tests/")


if __name__ == "__main__":
    main()
