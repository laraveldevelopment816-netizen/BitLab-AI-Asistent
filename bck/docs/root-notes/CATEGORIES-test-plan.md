# Kategorije — test po test plan

> Cilj: 25/48 → 48/48 PASS u `evals/sets/categories_cold.json` (post-SSOT).
> Pristup: jedan failing test → fix → re-run. Ne paraleliziramo.

## 1. Failing klasifikacija (post-SSOT 11:59)

Iz [SSOT-eval-delta-analysis.md](./SSOT-eval-delta-analysis.md):

- **NULL routing (9):** Skeneri, HDD storage, Graficke kartice, Projektori, Fiksna telefonija, Kućišta, Rezervni dijelovi elektronika, Optika interna, Produženje garancije. Claude ne ruta na leaf iako je u enumu.
- **Parent-vs-leaf (~4):** Inkjet / Kopir / Foto / Matricni printeri — Claude bira parent 97, eval traži leaf.
- **Drift cat (~5):** proizvodi u status=0 cat-ovima (277 "Ostalo", 224 "Monitori") — "27 inch monitor", "gaming miš do 100 KM".
- **NEG_REGRESSION (3):** "namještaj", "biciklo", "gaming laptop do 100 KM" — search umjesto escalate.
- **Eval entry bug (1):** "HP printer" `expected_cat_id=125` (fantom).

## 2. Workflow

1. `python evals/run_categories.py --cat-id <id> --label probe-<n>` (ili `--query "<upit>"` za negativne entry-je koji nemaju cat_id).
2. Otvori HTML, klasifikuj failure u jedan od 5 bucket-a.
3. Jedan fix u jednom fajlu (prompt | override | eval entry | safety net).
4. Re-run isti test, potvrdi PASS. Tek tada sljedeći.

## 3. Preduslov — dorada alata

`run_categories.py` nema `--cat-id`/`--query` flag. Dodati u istom patch-u oba:

- `--cat-id <id>` — primarni za 235 auto-gen entry-ja (cat_id je unikatan, query nije: "Eksterni HDD" se pojavljuje 2× za cat 225 i 327).
- `--query "<upit>"` — fallback za 10 negativnih entry-ja bez `expect.category_id` i ad-hoc upite.

Patch lokacija: `evals/run_categories.py` `argparse` + `load_queries` (~5-10 linija). Bez toga svaki probe traži ad-hoc JSON.

## 4. Prvi test — Skeneri (NULL routing)

Razlog: najjasniji failure mode, 9 srodnih testova padaju isto. Ako Skeneri prolazi nakon nudge-a, vjerovatno padaju i ostali NULL leaf-ovi zajedno.

1. Baseline: `--cat-id 131 --label skeneri-baseline` (potvrda NULL routinga).
2. Provjeri da je cat 131 u enumu `search_products` (iz `data/categories_new.json`).
3. Nudge u `app/system_prompts.py` — primjer da leaf ime → `search_products` direktno.
4. Re-run `--cat-id 131 --label skeneri-fix`. Ako PASS, testiraj drugih 8 NULL leaf-ova jedan po jedan po cat ID-ju.

## 5. Redoslijed (ne sad)

1. NULL routing (krenuli sa Skeneri) → 2. Eval entry bug → 3. NEG_REGRESSION → 4. Drift cat (override vs rekategorizacija) → 5. Parent-vs-leaf strict.

## 6. Pravila

- Eval set je invariant ([[feedback-test-case-invariant]]) — entry mijenjamo samo kad je sam po sebi pokvaren (HP printer cat=125).
- Jedan fix u jednom trenutku ([[feedback-one-fix-at-a-time]]).
- Baseline + fix run za svaki test (A/B compare u `evals/runs/`).
- Druga instanca radi paralelno — sinhronizacija kroz log, ne dupliramo fix-eve.
