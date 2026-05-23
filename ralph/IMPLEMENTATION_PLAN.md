# IMPLEMENTATION_PLAN.md — Ralph state za bitlab-ai-asistent

Plan koji Ralph čita i ažurira. Bira top task iz Now, implementira, commit-uje, premješta u Done.

## Now

### 1. Generiši auto-gen kategorija eval set

**Acceptance**: `evals/sets/categories.jsonl` ima ≥30 entry-ja (parent + leaf iz `data/categories_new.json`). Skripta `scripts/gen_categories_eval.py` deterministička (isti input → isti output, verifikovano unit testom).

**Spec**: `specs/categories.md` §2 (auto-gen pravila).

**Konkretni koraci**:
- Provjeri postojanje `data/categories_new.json`; ako nema — cherry-pick iz `bck/data/categories_new.json` (sa attribucijom u commit message-u).
- `scripts/gen_categories_eval.py` čita JSON, generiše: za svaki leaf → `{tool: search_products, args.category_id: leaf.id}`, za parent sa ≥2 djece → `{tool: category_overview, args.category_id: parent.id}`.
- Write u `evals/sets/categories.jsonl` (jedan entry per line).
- Unit test: `tests/unit/test_gen_categories_eval.py` validira schema (sve linije parse-uju kao JSON, sva polja prisutna) + determinizam (dva poziva, byte-identical output).

### 2. Dodaj `category_overview` tool u `app/agent.py`

**Acceptance**: prvi parent entry u `categories.jsonl` → eval routing PASS (tool zvan sa očekivanim category_id). Handler stub vraća listu djece iz `data/categories_new.json`. Integration test sa mock_anthropic verifikuje tool dispatch.

**Spec**: `specs/categories.md` §3 (tool schema).

### 3. Dodaj `search_products` tool u `app/agent.py`

**Acceptance**: prvi leaf entry → eval routing PASS. Handler stub vraća prazan list (`{"products": []}`); pravi RAG dolazi u Fazi 2. Integration test verifikuje dispatch.

**Spec**: `specs/categories.md` §3.

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

(prazno — Ralph dodaje ovdje sa svakim PASS commit-om u formatu `- YYYY-MM-DD <sha> Naslov task-a`)
