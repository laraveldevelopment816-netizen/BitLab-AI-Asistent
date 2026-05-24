# IMPLEMENTATION_PLAN.md — Ralph state za bitlab-ai-asistent

Plan koji Ralph čita i ažurira. Bira top task iz Now, implementira, commit-uje, premješta u Done.

## Now

_(prazan — sljedeća iteracija bira top task iz Next)_

## Next

- **Sistem prompt v1**: minimum instrukcija "ako upit liči na kategoriju, pozovi `category_overview`/`search_products`". Acceptance: routing PASS rate ≥50% na cijelom `categories.jsonl`.
- **Negativni entry-ji**: `categories_manual.jsonl` (10-20 entry-ja: `not_in_catalog`, `ambiguous_name`, `typo_likely`, `out_of_scope`) + system prompt instrukcija za `tool=null` na out-of-scope. Acceptance: negativni routing PASS ≥80%.
- **Eval acceptance Faze 1**: cijela suite PASS rate ≥95%.
- **Spec products**: `specs/products.md` detaljan (RAG, schema, primjeri).

## Later

- **Faza 2**: RAG za `search_products` (cherry-pick iz `bck/app/rag.py`).
- **Faza 3**: cross-reference (multi-tool sekvence, filteri cijena/brand).
- **Regression set**: snapshot prvih 10 PASS entry-ja iz svake faze.
- **CI nightly eval**: GH Actions cron, real-LLM na staging.
- **Voice/email moduli**: out of scope za ovu inicijativu.

## Done

- 2026-05-24 5873704 `search_products` tool u OBA runnera (Anthropic shape + OpenAI derivacija) sa query/category_id/brand/min_price_km/max_price_km poljima. Handler stub vraća `{"products": []}` (RAG u Fazi 2). Mapping splittan u `_parent_block()` (36 parent ID) i `_leaf_block()` (220 leaf ID) — model za leaf upit više ne bira category_overview. Integration testovi za oba backenda + handler unit test. Eval client timeout 30s → 120s (PWR cold-start). Live eval (limit 2 fail-fast, kroz PWR): `cat-parent-17` PASS (category_overview/17) + `cat-leaf-93` PASS (search_products/93). Rate 100%.
- 2026-05-24 087861a `category_overview` tool u OBA runnera (`_run_anthropic` Anthropic shape + `_run_pwr` OpenAI shape derivacija). Handler stub vraća djecu iz `data/categories_new.json`. Tool dispatch loop + `app/tools.py` modul. Integration test sa mock_llm × oba backenda. Live eval (limit 1, kroz PWR) — prvi parent entry `cat-parent-17` "Računari" → PASS 100%.
- 2026-05-24 3d928f6 Generiši auto-gen kategorija eval set (250 entry-ja: 220 leaves + 30 parents; deterministička skripta, schema + determinizam unit testovi)
