# Eval Refactor v2 — `runtime_eval.py` kao jedini nosilac

**Premisa:** ono što stvarno mjerimo je end-to-end ponašanje sistema (Claude +
tool + DB + prompt). Deterministički `handle_*` test mjeri samo da Python
funkcija radi — to je unit test, ne eval. Eval = LLM u petlji, inače je
beskoristan kao regression signal nakon prompt/tool-desc izmjena.

## Arhitektura

`evals/runtime_eval.py` — generalizacija postojećeg
`visualize_parent_runtime.py`. Jedan engine, više eval setova, jedan HTML
report sa per-set sekcijama. `--label` ostaje za A/B compare. Sve ostale
`run_*` skripte se brišu ili postaju thin wrapperi.

## Eval setovi (JSON-driven, ne kod)

| Set | Šta testira | Verdict polja |
|---|---|---|
| `bare_parent.json` | "Mobiteli", "TV" → očekuje `category_overview(parent_id=X)` | `tool_chosen`, `args_match`, `children_listed≥3` |
| `qualified.json` | "gaming miš do 100KM" → `search_products` sa filterima | `tool_chosen`, `products_in_subtree%`, `price_filter_applied` |
| `ambiguous.json` | "nešto za gaming" → bilo overview bilo search, ali ne fallback | `tool_chosen∈{allowed}`, `no_hallucination` |
| `regression.json` | bug-specifični upiti (parent_id expansion bug, itd.) | per-case custom expect |

Svaki entry:

```json
{
  "query": "...",
  "expect": {
    "tool": "search_products",
    "args_subset": {"category_id": "123"},
    "category_subtree": "123",
    "min_results": 3,
    "forbid_products": ["G12345"]
  }
}
```

Engine zna kako svaki expect ključ da provjeri.

## Coverage auto-gen

`scripts/gen_eval_set.py` čita `PARENT_CATEGORIES` iz `app/tools.py` i
regeneriše `bare_parent.json` (≥90% parenta sa ≥2 djece). Ručno održavani
samo `regression.json` i `ambiguous.json`.

## Output

Jedan HTML sa kolapsabilnim sekcijama po setu, top-line metrika
(`pass/fail/wrong_tool/wrong_args/hallucination` count), diff vs prethodni
`--label` run.

## Deterministički `sim_*` testovi

Ne brišu se, ali se sele u `tests/` kao pytest unit testovi
(`handle_category_overview` returns shape X). Nisu eval, nisu u HTML
reportu, voze se na svaki commit. Eval voziš ručno / nightly.

## Plan koraka

1. Generalizovati `visualize_parent_runtime.py` → `runtime_eval.py` (loader
   uzima listu eval set fajlova, expect-evaluator je pluggable).
2. Definisati JSON schema za expect (`tool`, `args_subset`,
   `category_subtree`, `min_results`, `forbid_products`).
3. Migrirati postojeći `parent_eval_set.json` u novi format kao
   `bare_parent.json`.
4. Dodati `qualified.json` (iz postojećeg `category_eval.json`, prevesti u
   novi expect format).
5. `scripts/gen_eval_set.py` za auto-coverage parenta.
6. Obrisati / spojiti `run_categories*.py`, `test_e2e_visual.py`,
   `run_e2e_html.py` — ono što ostane korisno (markdown parser, HTML
   renderer) iz `runtime_eval.py` postaje `evals/_lib.py`.
7. `sim_*` testovi iz starog plana → `tests/test_tools_unit.py`, ne u
   evalima.

## Šta ovo rješava što v1 nije

- Primarni signal je realno ponašanje, ne Python unit.
- A/B compare preko `--label` je first-class.
- Coverage je auto-generated.
- Jedan report umjesto tri skripte.
