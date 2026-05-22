"""run_products.py — eval engine za pretragu proizvoda (kvalifikovani upiti).

Mjeri: za upit sa kvalifikatorom (cijena, brend, model, namjena) — da li je
Claude pozvao search_products sa adekvatnim filterima, i da li su vraćeni
proizvodi relevantni (in-subtree, in-price-range, brand match).

Eval setovi: evals/sets/products_cold.json (i kasnije evals/sets/multi_turn.json
za kontekstualne upite).

Output: evals/runs/products-<label>-<timestamp>.html.

PLACEHOLDER — implementacija slijedi. Dashboard ima sva search_products polja
(brand_id, top_k, max_price_km), koja u evals/archives/visualize_parent_runtime.py
nisu bila u fokusu jer je taj engine bio prilagođen kategorijskoj evaluaciji.
"""
