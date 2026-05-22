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
├── categories.csv            ← AUTORITATIVAN export iz baze (status, parent_id)
├── categories.json           ← derivat: SAMO leaf kat. sa proizvodima (50 cat-ova)
│                               KORISTI: app/tools.py (Claude enum + description)
├── categories_new.json       ← NOVO: pun export svih 255 kategorija sa
│                               h1_title, intro_text, urlhash, super_id, parent_id.
│                               TBD: zamijeniti categories.json kao izvor labela.
├── category_terms.json       ← BCS sinonimi po kategoriji (term → cat_id)
│                               KORISTI: app/rag.py — SOFT boost (+0.25)
└── brend.json                ← brendovi + priority (vidi ai-search-improvements.md)
```

**Tabela uloga:**

| Datoteka | Sadrži parent-e? | Ko čita | Šta radi |
|---|---|---|---|
| `categories.csv` | ✓ (parent_id kolona) | `app/rag.py:_load_cat_descendants` | gradi {cat → descendants} mapu |
| `categories.json` | ✗ (samo 50 leaf-eva) | `app/tools.py:60` | Claude enum + label tekst u tool description |
| `categories_new.json` | ✓ (svih 255) | — (zasad nigdje) | budući izvor labela kad ga uključimo |
| `category_terms.json` | ✓ ("mobiteli"→{151}) | `app/rag.py:_detect_intent_categories` | soft boost kad Claude ne pošalje cat_id |

---

## 2. Tok jednog upita

```
USER "Mobiteli"
   │
   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Claude (app/agent.py:_run_anthropic / _run_pwr)                     │
│                                                                     │
│  Vidi enum cat-ova iz categories.json (50 entry-ja, SAMO leaf).     │
│  Bira: 175 "Mobilni telefoni"  (parent 151 NIJE u enumu!)           │
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
parent_id stablo iz categories.csv (samo status=1):

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
| User piše tačno ime parent kat. ("Mobiteli", "Računari") | Claude bira leaf descendant; vraća samo dio porodice | "category_overview" tool sa breakdown-om po djeci ([covt task u STATUS.md](../../STATUS.md)) |
| `categories.json` filtrira parent kat. bez direktnih proizvoda | Claude ih ne vidi | uključiti iz `categories_new.json` (kad odlučimo) |
| `super_id` grupisanje (4 = mobile/TV/audio, vidi `categories_new.json`) | Ignorisano | TBD: druga runda navigacije ako bude trebalo |
| Parent expansion na hard filter | Radi ✓ | — |
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
