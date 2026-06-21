# SSOT refaktor — kategorije i brendovi

> **Kontekst:** [EVAL-failure-analysis-2026-05-23.md](./EVAL-failure-analysis-2026-05-23.md)
> identifikuje da Claude rutira ~7 printer upita na nepostojeću kategoriju 125
> jer `search_products` enum vidi stari 50-bucket fajl. Ovaj dokument je plan
> kako da se svi izvori kategorija/brendova svedu na **jedan fajl po domenu**
> + **jedan loader modul**, tako da promjena taxonomy-ja postaje jedna izmjena.

## Status implementacije — 2026-05-23

Plan je u potpunosti implementiran. Sažetak:

| Korak | Status | Komentar |
|---|---|---|
| 1. Pripreme (baseline + overrides export) | ✅ | `data/category_label_overrides.json` (50 ručnih labela); MD5 starog `_CATEGORIES_BLOCK` (50 entries): `2739a7033bff3ab010abdd6263503635` (2464 B) |
| 2. Novi modul `app/categories.py` + `app/brands.py` | ✅ | CATEGORIES (238 aktivnih), PARENT_CATEGORIES (26), CAT_DESCENDANTS (238), ACTIVE_IDS/ALL_IDS; BRANDS_SORTED (89). `tests/test_categories_ssot.py` 8/8 parity sa starim loader-ima. |
| 3+4. Migracija `app/tools.py` + label override | ✅ | `_CATEGORIES_BLOCK` sad 117 leaf cat-ova sa ≥1 proizvod (umjesto 50 bucket-a) — render 5184 B vs 2464 B. `_CATEGORY_IDS` enum 117 entries. |
| 5. Migracija `app/rag.py` | ✅ | `_load_cat_descendants` i `_load_brands` uklonjeni; sada `from .categories import CAT_DESCENDANTS` i `from .brands import BRANDS`. |
| 6. `scripts/build_category_terms.py` + evals na JSON | ✅ | Skripta čita `categories_new.json` umjesto CSV-a. `evals/run_categories.py`, `evals/run_products.py`, `tests/test_parent_expansion.py` migrirani. |
| 7. Brisanje starih fajlova | ✅ | `git rm data/categories.json data/categories.csv scripts/build_categories.py`. Docs (`docs/getting-started.md`, `docs/architecture.md`) ažurirane. |
| 8. Eval delta | ⏳ | Pokrenuti `evals/run_categories.py` (smoke 50) + `evals/run_products.py` (21) **nakon ovog commit-a** da uhvatimo before/after. Očekivano: Cluster A (7 printer OUT) nestaje; Cluster B (17 NULL) djelimično se smanjuje (sad 117 cat-ova u enum-u umjesto 50 bucket-a). |

Drift u `category_terms.json` regen-u (od 89 → 88 cat-ova sa terminima):
cat 395 ("4G ROUTERI", status=NULL) i cat 224 ("Monitori", status=0) više
nisu uključeni jer SSOT filter je `status=1`. Stari CSV loader nije pravio
ovu razliku. Ovo je namjerno smanjenje — neaktivni cat-ovi neće biti u
`_CATEGORY_IDS` enum-u pa nemaju ni razlog biti u term boost mapi.

Test rezultati: 76 passed, 1 skipped (CSV parity, expected po brisanju
CSV-a). Padajuće testove izvan refaktora (test_typo_robustness,
test_custom_build_response, dio test_brand_category_search.TestBrandSearch)
pokreću PWR backend kroz claude-cli subprocess — flakiness je dokumentovan u
STATUS kartici `pwhk` i nije uzrokovan ovim refaktorom.

## Ispravke u odnosu na originalnu analizu

EVAL-failure-analysis-2026-05-23.md zadržan je u originalnoj formi za
nezavisan review. Ove dvije tvrdnje iz njegove tabele su **netačne** i
treba ih čitati kako slijedi:

| u dokumentu piše | tačno je |
|---|---|
| `categories_new.json` — 255 entries (real taxonomy, **status=1**) | 255 entries, ali **uključuje sve statuse**: 238×`status=1`, 11×`status=0`, 6×`NULL` |
| `categories.csv` — **513 entries** (full taxonomy uključujući inactive) | **255 redova** / 513 linija (`wc -l` broji embedded newline-ove u HTML `description` polju). Skup ID-eva je **identičan** sa `categories_new.json` (provjereno: `csv_ids ∩ json_ids = svih 255`) |
| u sekciji "Korak 1 — Završi migraciju": "[`_load_categories()` čita] sve `status=1` kategorije" | Treba čitati: **sve kategorije iz `categories_new.json`, po potrebi filtrirati `status=1`**. Originalna formulacija implicira da `status=1` mora biti hard-coded u loader-u, što je prerano ograničenje — odluka o filtriranju zavisi od konteksta: enum za `search_products` treba samo aktivne, ali npr. `category_label_overrides.json` (korak 4) treba moći referencirati i ID-eve van `status=1` skupa |

Posljedica za refaktor: CSV ne nosi nikakve dodatne ID-eve van JSON-a, pa
je njegovo brisanje (korak 7) bezopasno — sve što hard filter izvlači iz
CSV-a već postoji u `categories_new.json` preko `parent_id` polja.

## Trenutno stanje (problem)

4 fajla za kategorije sa **nepoklapajućim key set-ovima**:

| fajl | keys | uloga danas | koristi |
|---|---|---|---|
| `data/categories.json` | 50 | enum + description za `search_products` | `app/tools.py:38, 121` |
| `data/categories_new.json` | 255 | enum za `category_overview` (parent breakdown) | `app/tools.py:39, 133` |
| `data/categories.csv` | 255 (red.) / 513 (lin.) | parent expansion u hard filter-u | `app/rag.py:26` |
| `data/category_terms.json` | 89 | BCS termini za intent boost u re-ranku | `app/rag.py:25, 220` |

Brendovi — 1 fajl ali **3 čitača**:

- `data/brend.json` čita se u `app/tools.py:97`, `app/rag.py:97`, `scripts/build_category_terms.py:32`.

**Posljedica:** ono što Claude vidi (50) ≠ ono što hard filter zna (255) ≠
ono što re-rank booster prepoznaje (89). ID 125 postoji **samo** u 50-bucket
fajlu — Claude ga halucinira jer mu je jedini "printer" match u enum-u.

## Ciljno stanje

```
data/categories_new.json     ← jedini taxonomy fajl (ručno održavan)
data/category_terms.json     ← derivat (auto-gen iz JSON-a, NE iz CSV-a),
                                ostaje na disku jer sadrži ručno tunirane
                                BCS sinonime/kolokvije
data/brend.json              ← jedini brand fajl

app/categories.py            ← JEDINI loader; importuje se odasvud
app/brands.py                ← JEDINI brand loader
```

Brisanje: `data/categories.json`, `data/categories.csv`.

## API koji `app/categories.py` izlaže

```python
# Učitano jednom pri importu, sve derivacije in-memory.

CATEGORIES: dict[str, dict]            # {cid: {label, urlhash, parent_id, status}}
                                       # za search_products enum + description
PARENT_CATEGORIES: dict[str, dict]     # parent_id=0 + ≥2 djece, za category_overview
CAT_DESCENDANTS: dict[str, set[str]]   # cid → {sebe + svi descendant-i}, za hard filter
                                       # (zamjena za _load_cat_descendants iz CSV-a)

ACTIVE_IDS: set[str]                   # samo status=1; koristi se gdje treba filtriranje
ALL_IDS: set[str]                      # uključujući status=0/NULL
```

`app/brands.py` analogno: `BRANDS`, `BRAND_IDS`, `BRANDS_BLOCK`.

## Koraci

### 1. Pripreme (read-only, eval baseline)

- Snimiti eval baseline (categories + products) **prije** refaktora.
- Zapisati MD5 trenutnog `_CATEGORIES_BLOCK` (rendered) — da znamo šta je
  Claude vidio do sada.
- Eksportovati listu od 50 ručno-tuniranih labela iz `categories.json` u
  novi fajl `data/category_label_overrides.json` (vidi korak 4).

### 2. Novi modul `app/categories.py`

- Učita `categories_new.json` jednom.
- Implementira sve tri derivacije (CATEGORIES, PARENT_CATEGORIES, CAT_DESCENDANTS).
- Replicira `status=1` filter koji `_load_cat_descendants` već radi.
- Unit-testovi: ekvivalentnost sa starim loader-ima na trenutnim podacima
  (`_load_cat_descendants(CSV) == CAT_DESCENDANTS(JSON)` za sve aktivne ID-eve).

### 3. Migracija `app/tools.py`

- Zamijeniti `_load_categories()`, `_load_parent_categories()`,
  `_CATEGORIES_PATH` referencama na `app/categories.py`.
- Obrisati `_CATEGORIES_PATH = _DATA_DIR / "categories.json"`.
- `_CATEGORIES_BLOCK` se sada renderuje iz **255 leaf ID-eva** umjesto 50.
  Treba odluka: cijela lista (token-cost ↑ ali Claude vidi sve), ili samo
  leaf cat-ovi sa proizvodima (`>0 products`).

### 4. Label override

`categories.json` ima labele tipa *"Printeri (raznovrsni — Epson, HP, Canon)"*
koje su **bogatije od** `name` polja u taxonomy-ju (*"Printeri raznovrsni"*).
Da se to znanje ne izgubi:

- `data/category_label_overrides.json` (mali fajl, ručan): `{cid: "custom label"}`
- `app/categories.py` primjenjuje override pri gradnji `CATEGORIES.label`
  (fallback na `name` ili `h1_title`).
- Override fajl **može imati ID-eve koji više ne postoje** u taxonomy-ju
  (npr. 125) — loader ih ignoriše uz warning log. To rješava drift problem.

### 5. Migracija `app/rag.py`

- Obrisati `_load_cat_descendants()` i `_CATEGORIES_CSV_PATH`.
- Importovati `CAT_DESCENDANTS` iz `app/categories.py`.
- `_load_brands()` premjestiti u `app/brands.py`, uvesti i u `tools.py`.

### 6. `category_terms.json` regen pipeline

- `scripts/build_category_terms.py` trenutno čita CSV. Prebaciti na
  `categories_new.json`.
- Dodati u CI/pre-commit check: key set u `category_terms.json` mora biti
  **podskup** `ACTIVE_IDS`. Ako nije — fail.

### 7. Brisanje starih fajlova

- `git rm data/categories.json data/categories.csv`
- Provjeriti da nigdje (uključujući `evals/`, `scripts/`) ne ostaje referenca.

### 8. Eval delta

- Pokrenuti isti eval set kao u koraku 1.
- Očekivano: 7 printer fail-ova nestaje (Claude sada vidi 124/126/127/...),
  Cluster A iz failure analize riješen.
- Ako neki novi fail-ovi iskaču (npr. zbog drugačijih label-a u enum-u),
  iterirati na `category_label_overrides.json`.

## Šta NE rješava ovaj plan

- **Token cost u tool description-u**: 255 linija umjesto 50 = ~5× više
  tokena u svakom toolu pozivu. Treba mjeriti i možda filtrirati na "ima
  ≥1 proizvod" (vjerovatno smanji na ~120-150).
- **Label kvalitet**: `name` iz taxonomy-ja je često goli ("Računari",
  "Printeri raznovrsni"). Override fajl pomaže, ali ne zamjenjuje
  copywriting pass nad svih ~150 leaf labela.
- **DB live source**: ovo i dalje učitava sa diska. Live DB pull je
  posebna kartica.

## Mapa: fajl → očekivane izmjene

```
app/tools.py            -large refactor (loader brisanje, importi)
app/rag.py              -medium refactor (loader brisanje, importi)
app/categories.py       +new
app/brands.py           +new
scripts/build_category_terms.py   -small (path swap CSV→JSON)
evals/run_categories.py            -small (CSV path → categories module)
evals/run_products.py              -small (isto)
data/categories.json               -delete
data/categories.csv                -delete
data/category_label_overrides.json +new (preneseno iz categories.json)
tests/test_categories_ssot.py      +new (parity sa starim loader-ima)
```
