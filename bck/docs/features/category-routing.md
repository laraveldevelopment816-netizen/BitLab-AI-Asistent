# Kategorijska pretraga — tok i izvori podataka

Vizuelna referenca za to **kako upit korisnika postaje izbor kategorije** u
search-u. Cilj dokumenta: kad mijenjamo bilo šta vezano za kategorije
(parent expansion, novi tool, `super_id` grupisanje, override prompt-a),
odmah se vidi koje datoteke učestvuju i ko ih čita.

> Sestrinski dokument: [`ai-search-improvements.md`](ai-search-improvements.md)
> (brand layer + ranking detalji).

---

## 1. Izvori podataka

```
data/
├── (taxonomy fajl)           ← AUTORITATIVAN export iz baze (255 entries)
│                               status, parent_id, name, h1_title, urlhash,
│                               super_id, meta_keywords.
│                               UČITAVA ga SAMO app/categories.py modul.
├── category_label_overrides.json
│                             ← ručno-tunirane bogatije labele (override
│                               nad name/h1_title) za poznate kategorije.
├── category_terms.json       ← BCS sinonimi po kategoriji (term → cat_id),
│                               auto-gen iz taxonomy entry-ja.
│                               KORISTI: app/rag.py — SOFT boost (+0.25)
└── brend.json                ← brendovi + priority (vidi ai-search-improvements.md)
```

**SSOT pravilo**: SAMO `app/categories.py` čita taxonomy fajl. Svi
ostali konzumenti (tools.py, rag.py, evals, scripts, tests) idu kroz
njegov public API: `CATEGORIES`, `PARENT_CATEGORIES`, `CAT_DESCENDANTS`,
`CHILDREN_OF`, `ACTIVE_IDS`, `ALL_IDS`, plus build-time helper
`iter_raw_entries()` za skripte kojima treba sirov pristup poljima.

**Tabela uloga:**

| API iz `app/categories.py` | Šta sadrži | Ko ga koristi |
|---|---|---|
| `CATEGORIES` (dict, 238 aktivnih) | label + count + parent_id po cat_id | `app/tools.py` — Claude enum + tool description |
| `PARENT_CATEGORIES` (dict, 26) | parent_id=0 sa ≥2 djece + children list | `app/tools.py:CATEGORY_OVERVIEW` |
| `CAT_DESCENDANTS` (dict) | cid → set(cid + svi descendant-i) | `app/rag.py` hard-filter parent expansion |
| `CHILDREN_OF` (dict) | parent_cid → direct children list | `evals/run_*.py` tree walking |
| `category_terms.json` | term → {cat_id} ("mobiteli"→{151}) | `app/rag.py:_detect_intent_categories` soft boost |

---

## 2. Tok jednog upita

```
USER "Mobiteli"
   │
   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Claude (app/agent.py:_run_anthropic / _run_pwr)                     │
│                                                                     │
│  Vidi enum cat-ova iz CATEGORIES (117 leaf-eva sa ≥1 proizvod,      │
│  iz app/categories.py SSOT-a).                                      │
│  Plus PARENT_CATEGORIES enum za category_overview tool.             │
│  "Mobiteli" → tačan match parent 151 → category_overview(151)       │
└─────────────────────────────────────────────────────────────────────┘
   │  tool_call: search_products(query="Mobiteli", category_id="175")
   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ RAG search (app/rag.py:376)                                         │
│                                                                     │
│  ① embed(query)  → vec_scores                                       │
│  ② BM25(query)   → bm25_scores                                      │
│  ③ fused = 0.6*vec + 0.4*bm25                                       │
│                                                                     │
│  ④ Soft boost (samo ako category_id is None):                       │
│       intent_cats = _detect_intent_categories(query)                │
│       koristi category_terms.json  →  +0.25 na proizvode u tim cat. │
│                                                                     │
│  ⑤ Hard filter (category_id postavljen → SKIP soft boost):          │
│       valid_cats = _cat_descendants[175] = {175}   (175 je leaf)    │
│       drop sve proizvode čiji categories_id ∉ valid_cats            │
│                                                                     │
│  ⑥ Sort: in_stock first, score buckets, brand priority tie-break   │
│  ⑦ Vrati top_k (default 5, EVAL_HARD_TEST=true → 200)               │
└─────────────────────────────────────────────────────────────────────┘
   │
   ▼
Claude renderuje odgovor → markdown lista → widget
```

**Ključno zapažanje:** ④ i ⑤ se **isključuju međusobno** — soft boost preko
`category_terms.json` radi *samo* kad Claude ne pošalje hard filter.
Trenutni tok za "Mobiteli" gađa ⑤ (jer Claude šalje 175), pa
`category_terms.json["151"] = ["mobiteli", ...]` nikad ne ulazi u igru.

---

## 3. Parent expansion — kad i kako

```
parent_id stablo iz app/categories.py SSOT-a (samo status=1):

  151 "Mobiteli" (parent_id=0)
  ├── 175 "Mobilni telefoni"        (166 proizvoda)
  ├── 176 "Bežične TWS / držači"   (129 proizvoda)
  └── 394 "Maske za mobitele"      (1.274 proizvoda)
                                   Σ = 1.575 u porodici

  17 "Računari" (parent_id=0)
  ├── 93  "Desktop Brand Name"
  ├── 98  "Notebook"
  ├── 99  "Tablet"
  ├── 233 "Desktop PC"
  └── 234 "Računari All-In-One"
```

**`_load_cat_descendants()`** (`app/rag.py:31`) gradi mapu jednom pri startu:

```
{
  "151": {"151", "175", "176", "394"},
  "175": {"175"},                       ← leaf, sam sebe
  "17":  {"17", "93", "98", "99", "233", "234", ...},
  ...
}
```

Hard filter u koraku ⑤ koristi `valid_cats = _cat_descendants[cid]` —
ako Claude pošalje 151, vraćaju se svi proizvodi iz cijele porodice.
**Ali Claude ne može poslati 151** dok god `categories.json` ne uključuje
parent-e.

---

## 4. Soft boost — `category_terms.json`

```
USER "najbolji laptop do 1500 KM"  (Claude ne šalje category_id)
   │
   ▼
_detect_intent_categories(query)
   │
   ├── tokenize + strip diacritics: ["najbolji", "laptop", "do", "1500", "km"]
   ├── BCS stop-words filter:        ["laptop", "1500"]
   ├── HEAD-NOUN match:              "laptop" → category_terms["98"] = ["laptop", ...]
   │                                            → hits = {98}
   └── return {98}
   ▼
boost = +0.25 na fused score svih proizvoda gdje categories_id == 98
```

**Mapping primjeri za mobile domain:**

| Term | Mapira na |
|---|---|
| `"mobiteli"` | {151} |
| `"mobilni telefoni"` | {151, 175} |
| `"mobitel"`, `"telefon"`, `"smartfon"` | {175} |
| `"maska za mobitel"`, `"futrola"` | {394} |
| `"dodaci za mobitele"`, `"držač za telefon"` | {176} |

Pravila u `_detect_intent_categories` (vidi `app/rag.py:329`):
- max 4 non-stop tokena (inače upit prelazi u long-tail režim, soft boost ne pomaže)
- head-noun fallback: ako prvi token ne match-uje, probaj drugi (npr. "gaming miš" → fallback "miš")
- bigram check za multi-word terme ("matična ploča", "fiksni telefon")

---

## 5. Edge case-ovi i poznata ograničenja

| Slučaj | Trenutno ponašanje | Šta bi trebalo |
|---|---|---|
| User piše tačno ime parent kat. ("Mobiteli", "Računari") | `category_overview` tool vraća breakdown po direktnoj djeci | — (riješeno) |
| Cat-ovi sa 0 proizvoda u taxonomy-ju | `CATEGORIES` ih izlaže (svi status=1), ali `_CATEGORY_IDS` enum (search_products) ih filtrira preko `get_active_ids_with_products(min_products=1)` | — |
| `super_id` grupisanje (npr. 4 = mobile/TV/audio) | Ignorisano | TBD: druga runda navigacije ako bude trebalo |
| Parent expansion na hard filter | Radi ✓ (preko `CAT_DESCENDANTS`) | — |
| Soft boost dok je hard filter aktivan | Skipped (by design) | — |

---

## 6. Mjesto za izmjene

Kad budemo radili novu feature pretrage, gledaj ovaj poredak datoteka:

1. **`app/tools.py`** — Claude tool schema (enum kategorija, opisi). Promjene
   ovdje mijenjaju šta Claude može **birati**.
2. **`app/system_prompts.py`** — instrukcije ponašanja (kad da pozove koji
   tool, kako da reaguje na parent upite).
3. **`app/rag.py`** — *kako* se filtrira i rangira. Hard filter, soft boost,
   parent expansion, brand priority — sve ovdje.
4. **`data/categories*.json`**, **`category_terms.json`** — izvori.
   Ako kategorija nije u izvoru, AI je nikad neće odabrati.
5. **`evals/parent_eval_set.json`** + **`evals/visualize_parent_runtime.py`**
   — verifikacija (HTML output u `evals/runs/`).

Vidi i:
- [evals/README.md](../../evals/README.md) za pokretanje servera + eval-a
- [ai-search-improvements.md](ai-search-improvements.md) za brand layer + ranking
