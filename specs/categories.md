# Spec — kategorije (Faza 1)

Rutiranje korisničkog upita u odgovarajuću tool akciju za webshop kategorije.

## §1 — Domen

Webshop ima hijerarhiju kategorija (root → parent → leaf), SSOT: `data/categories_new.json`. Korisnik upitom kao "Mobiteli", "Skeneri ispod 50 KM", "Imate li Samsung tablete?" očekuje da agent ili (a) pokaže pregled potkategorija (parent), (b) vrati listu proizvoda (leaf), ili (c) odbije out-of-scope upit.

## §2 — Auto-gen pravila

`scripts/gen_categories_eval.py` generiše `evals/sets/categories.jsonl` po pravilima:

- **Leaf** (kategorija bez djece): entry `{tool: "search_products", args.category_id: leaf.id}`.
- **Parent sa ≥2 djece**: entry `{tool: "category_overview", args.category_id: parent.id}`.
- **Query**: ime kategorije (ili sinonim ako postoji `data/category_terms.json`).
- **History**: prazno (cold start).
- **Tags**: `["auto-gen", "leaf"]` ili `["auto-gen", "parent"]`.

Skripta mora biti deterministička: isti `categories_new.json` → byte-identical JSONL output. Verifikuje se unit testom (dva poziva, byte compare).

## §3 — Tool schema

### category_overview

```json
{
  "name": "category_overview",
  "description": "Prikaži pregled potkategorija unutar parent kategorije.",
  "input_schema": {
    "type": "object",
    "properties": {
      "category_id": {"type": "integer", "description": "ID parent kategorije."}
    },
    "required": ["category_id"]
  }
}
```

### search_products

```json
{
  "name": "search_products",
  "description": "Pretraga proizvoda po query stringu i opcionim filterima.",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Slobodni tekst pretrage."},
      "category_id": {"type": "integer", "description": "Suzi na leaf kategoriju."},
      "brand": {"type": "string", "description": "Filter brenda (npr. 'Samsung')."},
      "max_price_km": {"type": "number"},
      "min_price_km": {"type": "number"}
    }
  }
}
```

## §3.1 — LLM backend imperative

Tool dispatch mora biti dostupan u OBA LLM runnera u `app/agent.py`:

- `_run_anthropic` — Anthropic `tools=[...]` parameter (Anthropic shape sa `input_schema`).
- `_run_pwr` — OpenAI `tools=[{"type":"function","function":{...}}]` parameter (derivacija iz Anthropic format-a). Stari kod referenca: `git show 3d4bc87:app/agent.py` (`ALL_TOOLS_OPENAI_SHAPE`).

Default backend (`LLM_BACKEND=pwr` u `.env`) ide kroz PWR jer štedi Anthropic API budžet. Vidi `ralph/AGENTS.md` § LLM backend dispatch i memoriju `llm_backend_pwr_imperative`.

## §4 — Negativni primjeri

Ručno održavani u `evals/sets/categories_manual.jsonl`:

- **not_in_catalog**: "knjige", "namještaj" → `expect: {tool: null}` (webshop ne prodaje).
- **ambiguous_name**: "kabl", "torba" → `expect: {tool: null}` ili overview ako ima jednu jasnu parent.
- **typo_likely**: "mobitejli", "raunari" → sistem može korigovati ili pitati clarification.
- **out_of_scope**: "kakvo je vrijeme?", "garancija?" → `expect: {tool: null}`.

## §5 — Acceptance Faze 1

`python -m evals.framework.runner --suite categories` → PASS rate ≥ 95% (toleriše par WARN scenarij entry-ja). Integration testovi sa mock_anthropic prolaze. CI green.
