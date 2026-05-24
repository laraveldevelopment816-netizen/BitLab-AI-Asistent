# IMPLEMENTATION_PLAN.md — Ralph state za bitlab-ai-asistent

Plan koji Ralph čita i ažurira. Bira top task iz Now, implementira, commit-uje, premješta u Done.

## Now

### 1. Dodaj `category_overview` tool u OBA LLM runnera (`app/agent.py`)

**Acceptance**: prvi parent entry u `categories.jsonl` → eval routing PASS (tool zvan sa očekivanim category_id). Tool definicija u `_run_anthropic` (Anthropic shape) **I** `_run_pwr` (OpenAI shape, derivacija — vidi `git show 3d4bc87:app/agent.py` za referencu `ALL_TOOLS_OPENAI_SHAPE`). Handler stub vraća listu djece iz `data/categories_new.json`. Integration test sa `mock_llm` + `force_backend_pwr` verifikuje tool dispatch kroz PWR put.

**Spec**: `specs/categories.md` §3 (tool schema) + §3.1 (backend imperative).

### 2. Dodaj `search_products` tool u OBA runnera (`app/agent.py`)

**Acceptance**: prvi leaf entry → eval routing PASS. Tool u `_run_anthropic` I `_run_pwr` (oba shape-a). Handler stub vraća prazan list (`{"products": []}`); pravi RAG dolazi u Fazi 2. Integration test sa `mock_llm` + `force_backend_*` fixture verifikuje dispatch.

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

- 2026-05-24 3d928f6 Generiši auto-gen kategorija eval set (250 entry-ja: 220 leaves + 30 parents; deterministička skripta, schema + determinizam unit testovi)
