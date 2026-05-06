"""
Generiše data/categories.json — top N kategorija iz products.meta.json sa
human-readable labelama, brojem proizvoda i tri primjera.

LABELS dict ispod je manuelno mapiran nakon vizuelnog pregleda imena
proizvoda po cat_id-u. Auto-fallback (najčešći leading token) postoji za
sigurnost ako se katalog promijeni i pojavi nova kategorija u top N.

Pokreni: python scripts/build_categories.py
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
META_PATH = PROJECT_ROOT / "data" / "products.meta.json"
OUT_PATH = PROJECT_ROOT / "data" / "categories.json"

TOP_N = 30

# Manuelno mapirani labeli — ovo je izvor istine. Auto-extract je samo
# fallback za nepoznate kategorije.
LABELS: dict[str, str] = {
    "394": "Maske, futrole i zaštitna stakla za telefone",
    "277": "Miševi",
    "221": "Žičane slušalice sa mikrofonom (gaming/multimedija)",
    "175": "Mobiteli",
    "226": "Toneri za laserske printere",
    "176": "Bežične bluetooth slušalice (TWS)",
    "393": "Digitalne gift kartice i online kredit",
    "137": "USB i data kablovi",
    "304": "Kancelarijski pribor (heftalice, alat, sitnice)",
    "229": "Tinte za inkjet printere",
    "220": "Tastature",
    "177": "Pametni satovi (smartwatch)",
    "314": "Punjači (zidni, auto, USB)",
    "298": "Mrežni patch kablovi i mrežni alat",
    "316": "Video kablovi (HDMI, DisplayPort, DVI, SCART)",
    "279": "Bluetooth zvučnici i soundbar",
    "165": "Nosači i stalci za TV i monitor",
    "163": "Televizori",
    "307": "Podloge za miš",
    "118": "Računarska kućišta (case)",
    "99": "Tableti",
    "202": "Power bank i prijenosne baterije",
    "289": "Adapteri, držači i dodaci za tablete/telefone",
    "98": "Laptopi i notebook računari",
    "224": "Monitori",
    "309": "Wi-Fi routeri i range extenderi",
    "270": "Mrežni switchevi",
    "257": "USB flash memorije (memory stickovi)",
    "104": "Torbe i ruksaci za laptop",
    "324": "Postolja, caddy i dodaci za notebook",
    # Dodaj nove ovde ako se promijeni katalog
}

# Stop riječi za auto-fallback (ako se pojavi nova kategorija)
_STOP = frozenset({
    "za", "i", "u", "na", "od", "do", "sa", "po",
    "the", "of", "for", "with",
    "kabal", "kabl", "cable",  # previše generične
})

_WORD_RE = re.compile(r"[A-Za-zČĆŠŽĐčćšžđ]+", re.UNICODE)


def _tokenize_leading(name: str, max_tokens: int = 3) -> list[str]:
    """Prvih do `max_tokens` alfabetskih tokena imena, lowercased."""
    tokens = _WORD_RE.findall(name)
    return [t.lower() for t in tokens[:max_tokens]]


def _auto_label(names: list[str]) -> str:
    """Fallback heuristika: najčešći leading bigram ili monogram."""
    bigrams: Counter[tuple[str, str]] = Counter()
    monograms: Counter[str] = Counter()
    for n in names:
        toks = [t for t in _tokenize_leading(n) if t not in _STOP]
        if not toks:
            continue
        monograms[toks[0]] += 1
        if len(toks) >= 2:
            bigrams[(toks[0], toks[1])] += 1

    if bigrams:
        (a, b), c = bigrams.most_common(1)[0]
        if c >= 0.3 * len(names):  # bigram dominira → koristi
            return f"{a.capitalize()} {b}"
    if monograms:
        a, _ = monograms.most_common(1)[0]
        return a.capitalize()
    return "Razno"


def main() -> None:
    if not META_PATH.exists():
        raise SystemExit(f"Nema {META_PATH}. Pokreni embed_products.py prvo.")

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    products = meta["products"]

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for p in products.values():
        cat = (p.get("categories_id") or "").strip()
        if cat:
            by_cat[cat].append(p)

    ranked = sorted(by_cat.items(), key=lambda x: -len(x[1]))
    top = ranked[:TOP_N]

    output: dict[str, dict] = {}
    missing_labels: list[str] = []

    for cat_id, prods in top:
        names = [p.get("name", "") for p in prods]
        if cat_id in LABELS:
            label = LABELS[cat_id]
        else:
            label = _auto_label(names)
            missing_labels.append(cat_id)

        # Tri reprezentativna primjera — uzmi prva 3 imena na lageru ako postoje
        on_stock = [p for p in prods if (p.get("kolicina") or 0) > 0]
        sample_pool = on_stock if on_stock else prods
        examples = [p.get("name", "")[:90] for p in sample_pool[:3]]

        output[cat_id] = {
            "label": label,
            "count": len(prods),
            "examples": examples,
        }

    total_top = sum(c["count"] for c in output.values())
    total_all = sum(len(v) for v in by_cat.values())
    coverage = 100 * total_top / total_all if total_all else 0

    OUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ {OUT_PATH.relative_to(PROJECT_ROOT)} — top {len(output)} kategorija")
    print(f"   Pokrivenost: {total_top:,} / {total_all:,} ({coverage:.1f}%)")
    if missing_labels:
        print(f"⚠️  {len(missing_labels)} kategorija bez ručnog labela "
              f"(koristi auto-fallback): {', '.join(missing_labels)}")
        print("   Razmotri dodati u LABELS dict ako su važne.")


if __name__ == "__main__":
    main()
