# Spec — proizvodi (Faza 2)

> **Status**: placeholder. Detaljnije popunjava Ralph plan mode nakon završene Faze 1.

RAG-bazirana pretraga proizvoda kroz `search_products(query, category_id?, brand?, max_price_km?, min_price_km?)`. Cherry-pick iz `bck/app/rag.py` (`load_index`, `search`, relevance threshold) — NE wholesale reuse.

Eval entries u `evals/sets/products.jsonl` — manualni početak iz top widget logova ako su dostupni u `bck/var/bitlab.db`, ili sintetički iz `data/products.meta.json` (top 30 kategorija × 1-2 query-ja).

## Acceptance Faze 2

`python -m evals.framework.runner --suite products` → PASS rate ≥ 90%. Faza 2 popunjava judge.verdict_result za `min_results` i `top_result_contains_any` (trenutno WARN placeholder).
