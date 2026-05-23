# Spec — cross-reference (Faza 3)

> **Status**: placeholder. Detaljnije popunjava Ralph plan mode nakon završene Faze 2.

Multi-tool kombinacije u jednom upitu: kategorija × cijena × brand. Primjeri:

- "skeneri ispod 50 KM" → `search_products(query="skener", max_price_km=50)`.
- "Samsung mobiteli" → `search_products(query="mobitel", brand="Samsung", category_id=151)`.
- "tableti do 200 KM brenda Lenovo" → `search_products(query="tablet", brand="Lenovo", max_price_km=200)`.

Moguće multi-step (agent prvo `category_overview` da disambiguira, pa `search_products` sa parent_id-em).

## Pravila prioriteta argumenata

- Eksplicitna cijena uvijek u args (regex `do/ispod/iznad N KM`).
- Brand iz query-ja pattern match (lista poznatih brendova).
- Kategorija iz semantic match-a (ako query ima category term).

## Acceptance Faze 3

`python -m evals.framework.runner --suite cross_reference` → PASS rate ≥ 85%. Regression set raste na 50+ entry-ja koji nikad ne padaju.
