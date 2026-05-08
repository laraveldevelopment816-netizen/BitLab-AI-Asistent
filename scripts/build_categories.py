"""
Generiše data/categories.json — top N kategorija iz products.meta.json sa
human-readable labelama, brojem proizvoda i tri primjera.

Izvor labela (po prioritetu):
1. LABEL_OVERRIDES — manuelno mapirani slučajevi gdje CSV name nije dovoljan
   (npr. cat 98 "Notebook" → "Laptopi i notebook računari" da AI bolje
   prepozna semantiku). Override je rezerva, ne primarni izvor.
2. data/categories.csv — `h1_title` (prvi segment do " – ") ili `name`. Ovo
   je izvor istine za >95% kategorija.
3. Auto-extract iz imena proizvoda (samo ako CSV row ne postoji).

Pokreni: python scripts/build_categories.py
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
META_PATH = PROJECT_ROOT / "data" / "products.meta.json"
CSV_PATH = PROJECT_ROOT / "data" / "categories.csv"
OUT_PATH = PROJECT_ROOT / "data" / "categories.json"

# Top N kategorija po broju proizvoda. Trenutno: 50 (rast od 30) — pokriva
# duži tail kategorija pa AI klasifikator ima bolji recall za nišne upite
# ("rezači papira", "platno za projektor"...). Token cost u system prompt-u:
# ~50 cat × ~50 char = ~2500 char = ~600 tokens po requestu.
TOP_N = 50

# Override map: cat_id → label. Koristi se SAMO kad CSV `h1_title`/`name`
# treba pojasniti za AI klasifikaciju (npr. CSV ima samo "Notebook" ali
# proizvodi su "laptop, notebook, prijenosni računar" — širi label pomaže
# AI-u da pogodi više sinonima).
LABEL_OVERRIDES: dict[str, str] = {
    "98": "Laptopi i notebook računari",
    # Cat 176 i 394 oba imaju maske/futrole, ali 394 je dedicirana maska kategorija
    # (1274 proizvoda, naziv "Maske za mobitele"). Cat 176 je miks dodataka — TWS,
    # držači, punjači. Da AI klasifikator ne kombinuje, label za 176 ističe NE-mask
    # dodatke tako da "masku za telefon" jasno ide u 394. Test test_typo_robustness
    # verifikuje ovaj split.
    "176": "Bežične TWS slušalice, držači i punjači za mobitel",
    "221": "Žičane slušalice sa mikrofonom (gaming/multimedija)",
    "279": "Bluetooth zvučnici i soundbar",
    "393": "Digitalne gift kartice i online kredit",
    "289": "Adapteri, držači i dodaci za tablete/telefone",
    "304": "Kancelarijski pribor (heftalice, alat, sitnice)",
    "316": "Video kablovi (HDMI, DisplayPort, DVI, SCART)",
    "324": "Postolja, caddy i dodaci za notebook",
    "298": "Mrežni patch kablovi i mrežni alat",
    "165": "Nosači i stalci za TV i monitor",
    # Cat 277: u CSV-u "Ostalo" (status=0), ali u proizvodima 45% miševi +
    # USB hub-ovi, HDMI/VGA kablovi, docking station-i — catch-all PC dodaci.
    "277": "Miševi i razni PC dodaci (USB hub, kablovi, docking)",
    # Cat 125: nema CSV reda; svi 19 proizvoda su printeri raznih brendova.
    "125": "Printeri (raznovrsni — Epson, HP, Canon)",
    # Cat 226 i 229: CSV ima samo "Toneri" / "Tinta" — preuzak label.
    "226": "Toneri za laserske printere",
    "229": "Tinte za inkjet printere",
    # Cat 137: "USB kablovi" je kraći od potrebnog — treba i data kablovi.
    "137": "USB i data kablovi",
    # Cat 201, 202: "Baterije" / "Punjive baterije" su preuski — treba pojasniti.
    "202": "Power bank i prijenosne baterije",
    "201": "Baterije (AA, AAA, 18650, alkalne)",
    # Cat 257: CSV ima "USB stickovi – Flash memorije", treba dodati keyword.
    "257": "USB flash memorije (memory stickovi)",
    # Cat 166: CSV ima "Ostala oprema za TV" — preuzak; daljinski + chromecast.
    "166": "Daljinski upravljači, TV box, Chromecast i ostala oprema za TV",
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
    """Fallback heuristika: najčešći leading bigram ili monogram. Koristi se
    samo ako i CSV row i LABEL_OVERRIDES ne postoje (rijetko)."""
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
        if c >= 0.3 * len(names):
            return f"{a.capitalize()} {b}"
    if monograms:
        a, _ = monograms.most_common(1)[0]
        return a.capitalize()
    return "Razno"


def _load_csv_labels() -> dict[str, str]:
    """Iz categories.csv: cat_id → razumna labela. Strategija:
    - Uzmi `h1_title` prvi segment do " – " (npr. "Notebook – Laptopi i ..."
      → "Notebook"; "Računari – Desktop, Laptop i All-in-One" → "Računari").
    - Ako h1_title nema separator ili je prazan, fallback na `name`.
    - Trim na 80 znakova."""
    if not CSV_PATH.exists():
        return {}
    out: dict[str, str] = {}
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            cid = (r.get("id") or "").strip()
            if not cid:
                continue
            h1 = (r.get("h1_title") or "").strip()
            name = (r.get("name") or "").strip()
            label = ""
            if h1 and h1 != "NULL":
                # Cijela h1 fraza je obično informativnija od name-a; zadržava
                # disambiguaciju ("Pametni satovi – Smartwatch i fitness narukvice"
                # bolje opisuje nego samo "Pametni satovi" za AI klasifikaciju).
                # Truncate na 80 znakova ako predug.
                label = h1[:80].rstrip(" -–")
            if not label and name and name != "NULL":
                label = name.replace("...", "").rstrip(", ")
            if label:
                out[cid] = label
    return out


def _resolve_label(
    cat_id: str,
    csv_labels: dict[str, str],
    product_names: list[str],
) -> tuple[str, str]:
    """Vrati (label, izvor). Izvor je 'override' / 'csv' / 'auto'."""
    if cat_id in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[cat_id], "override"
    if cat_id in csv_labels:
        return csv_labels[cat_id], "csv"
    return _auto_label(product_names), "auto"


def main() -> None:
    if not META_PATH.exists():
        raise SystemExit(f"Nema {META_PATH}. Pokreni embed_products.py prvo.")

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    products = meta["products"]

    csv_labels = _load_csv_labels()
    print(f"→ Učitano {len(csv_labels)} labela iz CSV-a.")

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for p in products.values():
        cat = (p.get("categories_id") or "").strip()
        if cat:
            by_cat[cat].append(p)

    ranked = sorted(by_cat.items(), key=lambda x: -len(x[1]))
    top = ranked[:TOP_N]

    output: dict[str, dict] = {}
    source_counts: Counter[str] = Counter()

    for cat_id, prods in top:
        names = [p.get("name", "") for p in prods]
        label, source = _resolve_label(cat_id, csv_labels, names)
        source_counts[source] += 1

        # Tri reprezentativna primjera — prva 3 imena na lageru ako postoje
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

    print(f"\n✅ {OUT_PATH.relative_to(PROJECT_ROOT)} — top {len(output)} kategorija")
    print(f"   Pokrivenost: {total_top:,} / {total_all:,} ({coverage:.1f}%)")
    print(f"   Izvori labela: override={source_counts['override']}, "
          f"csv={source_counts['csv']}, auto={source_counts['auto']}")
    if source_counts["auto"]:
        auto_cats = [
            cid for cid, info in output.items()
            if info["label"] not in LABEL_OVERRIDES.values()
            and cid not in csv_labels
        ]
        print(f"⚠️  Auto-labelirane kategorije (nema u CSV-u): {', '.join(auto_cats)}")
        print("   Razmotri dodati u CSV ili LABEL_OVERRIDES ako su važne.")


if __name__ == "__main__":
    main()
