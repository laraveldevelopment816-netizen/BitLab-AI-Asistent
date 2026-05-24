# IMPLEMENTATION_PLAN.md — Ralph state za bitlab-ai-asistent

Plan koji Ralph čita i ažurira. Bira top task iz Now, implementira, commit-uje, premješta u Done.

## Now

- **Sistem prompt v1 u oba runnera** — Dodaj minimum instrukcija ("Webshop agent. Kad upit imenuje kategoriju ili proizvod iz kataloga, pozovi `category_overview` za parent kategorije ili `search_products` za leaf kategorije / konkretne upite. Out-of-scope upit = ne zovi tool, odgovori prirodno.") u `_run_anthropic` (`system=` parametar) i `_run_pwr` (`{"role": "system", "content": ...}` prva poruka). Sistem prompt mora biti single source — definisan u `app/agent.py` kao konstanta (npr. `SYSTEM_PROMPT_V1`), ne hardcoded inline u oba runnera. Acceptance: pytest unit test verifikuje da konstanta nije prazna i da je prosljeđena u oba backenda (mock_llm captures system arg / system message); eval cijela `categories.jsonl` (250 entry-ja) kroz PWR PASS rate ≥50%. Spec: `specs/categories.md` §1, §3, §3.1.
- **Negativni entry set `categories_manual.jsonl`** — Kreiraj 10-20 ručno napisanih entry-ja sa `expect.tool=null` po §4 spec-a: `not_in_catalog` (knjige, namještaj), `ambiguous_name` (kabl, torba), `typo_likely` (mobitejli, raunari), `out_of_scope` (vrijeme, garancija). Tag-uj `["manual", "negative", "<subtype>"]`. Sistem prompt refinement da prepozna out-of-scope (dopuna v1 instrukcija). Acceptance: cat-manual suite kroz PWR negativni routing PASS ≥80%; cijela `categories.jsonl` PASS rate ne smije pasti ispod ≥50% sa novim sistem promptom. Spec: `specs/categories.md` §4.
- **Analiza fail patterns nakon v1 baseline** — Pokreni `python -m evals.framework.runner --suite categories` (cijela suite, bez fail-fast, kroz PWR) sa najnovijim sistem promptom. Parse JSONL, izlistaj top 3-5 fail patterns kao konkretne nove task-ove u Next sekciji (npr. "leaf 47 Mobiteli — model bira category_overview umjesto search_products" ili "parent X — model halucinira djecu"). Acceptance: novi targeted fix task-ovi u Next sekciji (3-5 stavki), izveštaj u commit poruci. Spec: `specs/categories.md` §5 (gap analysis).

## Next

- **Faza 1 acceptance ≥95% PASS** — Umbrella: cijela `categories.jsonl` (250) + `categories_manual.jsonl` (10-20). Razbija se iterativno na konkretne fix task-ove iz fail patterns analize.
- **Spec `specs/products.md` detaljan** — RAG, schema, primjeri (priprema za Fazu 2). Trenutno placeholder. Spec: `specs/products.md` (revidiraj).

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
