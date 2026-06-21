# evals/ — Eval framework za BitLab AI asistent

Mjeri stvarno ponašanje `/api/chat` endpoint-a na realnim upitima i daje
deterministički PASS/WARN/FAIL po upitu. LLM je u petlji (Claude bira tool i
argumente), ali validacija output-a je čist kod — bez LLM judge.

## Struktura

```
evals/
├── run_categories.py        # engine: kategorijsko rutiranje (overview vs search)
├── run_products.py          # engine: pretraga proizvoda (kvalifikovani upiti)
├── sets/                    # eval setovi (JSON, unifikovan schema)
│   ├── categories_cold.json   # bare kategorijska imena, history=[]
│   ├── products_cold.json     # kvalifikovani product upiti, history=[]   (TODO)
│   └── multi_turn.json        # UX flow sa istorijom razgovora           (TODO)
├── runs/                    # HTML izvještaji (gitignored)
└── archives/                # stari engine i eval setovi (pre-refactor)
```

## Eval entry schema (unifikovan kroz sve setove)

```json
{
  "query": "Mobilni telefoni",
  "history": [],
  "expect": {
    "tool": "search_products",
    "category_id": "175",
    "args_subset": {"max_price_km": 100}
  },
  "tags": ["auto-gen", "leaf"]
}
```

Polja koja ne važe za upit se izostavljaju. Engine zna kako da svaki ključ
obradi — `tool` provjerava routing, `category_id` provjerava ID, `args_subset`
provjerava argumente koje je Claude prosledio.

Negativni entry-ji imaju `expect.failure_reason` (`not_in_catalog`,
`ambiguous_name`, `typo_likely`, `out_of_scope`) i `expect.tool: null` — sistem
treba pravilno da odbije, ne da prosledi tool poziv.

## Pokretanje

```bash
python evals/run_categories.py                          # cijeli categories_cold set
python evals/run_categories.py --limit 5                # smoke test
python evals/run_categories.py --label v2-prompt-fix    # za A/B compare nakon promjene
python evals/run_products.py --sets products_cold       # samo jedan set (kasnije)
```

Engine pravi HTML u `evals/runs/<engine>-<label>-<timestamp>.html`.

## Auto-gen pozitivnih entry-ja

`categories_cold.json` se generiše iz `data/categories_new.json` — leaf
kategorija dobija expected `search_products`, parent sa ≥2 djece dobija
expected `category_overview`:

```bash
python scripts/gen_categories_eval.py
```

Negativni primjeri su u skripti ručno održavani — auto-gen ih ne dira. Skripta
je idempotentna; ponovni run regeneriše JSON deterministički.

## Pravila

- **Eval setovi su invariant.** Ne mijenjaju se kad mijenjamo prompt. Mijenjaju
  se samo kad mijenjamo *šta testiramo* (novi scenario, novi tool, novi tag).
- **Jedan fix u jednom trenutku.** Kad mijenjamo prompt: jedan run prije, jedan
  poslije. Paralelna izmjena instrumenta + sistema gubi causal link.
- **Coverage auto-gen** za sve što struktura podataka može da iznese
  (kategorije, brendovi) — ručno održavamo samo ono što struktura ne zna
  (negativni primjeri, history scenariji).
- **Verdict pipeline:** `routing_verdict` → `result_verdict` → `overall_verdict`.
  Overall sjedinjuje routing i result u jedan PASS/WARN/FAIL signal po upitu
  (banner, leaderboard, terminal sažetak koriste overall; granularne metrike
  ostaju u sekciji "Razrada rute").

Detaljnu motivaciju i istoriju refactor odluka vidi u
`docs/brainstorm/2026-05-22-eval-framework-standardizacija/log.md`.
