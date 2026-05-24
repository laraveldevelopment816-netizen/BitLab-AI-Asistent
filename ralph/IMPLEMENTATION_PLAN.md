# IMPLEMENTATION_PLAN.md — Ralph state za bitlab-ai-asistent

Plan koji Ralph čita i ažurira. Bira top task iz Now, implementira, commit-uje, premješta u Done.

## Now

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

- 2026-05-24 59ce28c `evals/sets/categories_manual.jsonl` negativni set (16 entries, expect.tool=null, 4×4: `not_in_catalog`/`ambiguous_name`/`typo_likely`/`out_of_scope`). SYSTEM_PROMPT_V1 dopuna typo guard bullet-om (model NE korigovaše typo automatski — pita clarification; spec § 4 dopušta tu granu). Eval kroz PWR (label `ralph-iter6-postfix`): cat-manual full 16 → PASS 15 / FAIL 1 → 93.8% (acceptance ≥80% ✓); categories sanity (limit 20/250) → PASS 19 / FAIL 1 → 95% (acceptance ≥50% ✓). Jedini cat-manual FAIL: `cat-manual-amb-baterija` → model dao `category_overview(160)` "Baterije i punjači" parent (spec § 4 dopušta overview za jasnu parent, ali eval framework strogi tool=null; entry ostavljen, eventualni refinement u sljedećoj iteraciji).
- 2026-05-24 3cdaa99 SYSTEM_PROMPT_V1 konstanta u `app/agent.py` (single source) prosljeđena u OBA runnera (`_run_anthropic` system= + `_run_pwr` prva poruka). Parent/leaf routing pravila + out-of-scope instrukcije (knjige, vrijeme, garancija → ne zovi tool). Unit testovi (test_system_prompt.py): konstanta nepraznja + imenuje oba toola. Recovery commit (Ralph iter 4 prekinut login expiry-jem prije commit-a; rad kompletan i kvalitetan, manualno commit-ovan).
- 2026-05-24 5873704 `search_products` tool u OBA runnera (Anthropic shape + OpenAI derivacija) sa query/category_id/brand/min_price_km/max_price_km poljima. Handler stub vraća `{"products": []}` (RAG u Fazi 2). Mapping splittan u `_parent_block()` (36 parent ID) i `_leaf_block()` (220 leaf ID) — model za leaf upit više ne bira category_overview. Integration testovi za oba backenda + handler unit test. Eval client timeout 30s → 120s (PWR cold-start). Live eval (limit 2 fail-fast, kroz PWR): `cat-parent-17` PASS (category_overview/17) + `cat-leaf-93` PASS (search_products/93). Rate 100%.
- 2026-05-24 087861a `category_overview` tool u OBA runnera (`_run_anthropic` Anthropic shape + `_run_pwr` OpenAI shape derivacija). Handler stub vraća djecu iz `data/categories_new.json`. Tool dispatch loop + `app/tools.py` modul. Integration test sa mock_llm × oba backenda. Live eval (limit 1, kroz PWR) — prvi parent entry `cat-parent-17` "Računari" → PASS 100%.
- 2026-05-24 3d928f6 Generiši auto-gen kategorija eval set (250 entry-ja: 220 leaves + 30 parents; deterministička skripta, schema + determinizam unit testovi)
