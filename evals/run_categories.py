"""run_categories.py — eval engine za kategorijsko rutiranje (bare parent + leaf upiti).

Mjeri: koji tool je Claude pozvao za upit koji je ime kategorije, i da li je
cat_id tačan (parent → category_overview, leaf → search_products).

Eval setovi: evals/sets/categories_cold.json (i kasnije evals/sets/multi_turn.json
za history scenarij).

Output: evals/runs/categories-<label>-<timestamp>.html.

PLACEHOLDER — implementacija slijedi. Inspiracija u evals/archives/visualize_parent_runtime.py,
ali engine je novi (čisti dispatch, samo kategorijski signal, bez search_products-specific polja).
"""
