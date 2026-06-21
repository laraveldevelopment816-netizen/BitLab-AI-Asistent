# SSOT migracija — summary

> Puni plan: [SSOT-categories-refactor-plan.md](./SSOT-categories-refactor-plan.md)
> Root cause: [EVAL-failure-analysis-2026-05-23.md](./EVAL-failure-analysis-2026-05-23.md)

**Problem:** 4 fajla za kategorije sa nepoklapajućim key set-ovima (50 / 255 / 255 / 89).
Claude vidi enum od 50 bucket-a u `search_products`, halucinira cat 125 za sve printer upite.

**Cilj:** 1 taxonomy fajl + 1 loader modul. Promjena kategorija = jedna izmjena.

## Koraci

1. **Baseline** — snimi eval run prije refaktora, eksportuj 50 ručnih labela iz `categories.json` u `data/category_label_overrides.json`.
2. **`app/categories.py`** — novi modul, učita `categories_new.json` jednom, izloži `CATEGORIES`, `PARENT_CATEGORIES`, `CAT_DESCENDANTS`. Parity unit-testovi vs stari loader-i.
3. **`app/tools.py` migracija** — obriši `_load_categories`/`_load_parent_categories`, importuj iz `app/categories.py`. `search_products` enum sada vidi sve aktivne leaf-ove umjesto 50 bucket-a.
4. **Label override** — `data/category_label_overrides.json` čuva ručno tunirane labele ("Printeri — Epson, HP, Canon") iz starog fajla. Loader primjenjuje override → fallback na `name`.
5. **`app/rag.py` migracija** — obriši `_load_cat_descendants` (CSV) i `_load_brands`, importuj iz `app/categories.py` i novog `app/brands.py`.
6. **`category_terms.json` regen** — `scripts/build_category_terms.py` prebaci sa CSV-a na JSON izvor. CI check: keys ⊆ `ACTIVE_IDS`.
7. **Brisanje** — `git rm data/categories.json data/categories.csv`.
8. **Eval delta** — pokreni isti eval set, očekuj nestajanje 7 printer fail-ova (Cluster A). Iteriraj na override ako iskoče novi fail-ovi.

## Izlaz

```
data/categories_new.json       ← jedini taxonomy fajl
data/category_label_overrides.json  ← ručne labele (mali fajl)
data/category_terms.json       ← derivat (auto-gen, BCS sinonimi)
data/brend.json                ← jedini brand fajl
app/categories.py              ← jedini kategorijski loader
app/brands.py                  ← jedini brand loader
```

Brisani: `categories.json`, `categories.csv`. Loader duplikacija ukinuta.
