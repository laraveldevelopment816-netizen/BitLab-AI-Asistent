# Eval refactor plan — pokrivanje `category_overview` tool-a

**Cilj:** 100% deterministički eval sistem (bez LLM-a u petlji za primarni
correctness signal) + ≥90% pokrivenost parent kategorija iz baze.

## Trenutno stanje

| Skripta | Tip | Šta radi |
|---|---|---|
| `visualize_parent_expansion.py` | **Deterministic simulator** | RAG hard filter before/after parent_id expansion fix-a. Bez LLM-a, bez servera, čist CSV+JSON. |
| `visualize_parent_runtime.py` | **Runtime (LLM in loop)** | Pravi `/api/chat` poziv za svaki upit iz `parent_eval_set.json`, hvata tool-call argumente, mapira proizvode na kategorije. **Samo bare parent upiti** ("Mobiteli", "TV"). |
| `parent_eval_set.json` | Eval set | 15 bare parent upita. |
| `category_eval.json` | Eval set | 29 kvalifikovanih upita ("gaming miš", "laptop do 1500 KM"). |
| `run_categories*.py` | Runner-i | Vjerovatno voze `category_eval.json` preko `/api/chat`. Treba audit. |
| `test_questions.json` | Tool dispatch eval | `expect_tool` + `expect_contains` polja. |
| `test_e2e_visual.py` / `run_e2e_html.py` | E2E | Treba audit. |

**Konfuzija:** "search_products kompletno riješen?" — Ne. Pokriven je sa **3
različite skripte iz različitih uglova** (expansion simulator, parent_runtime,
category_eval runner-i). Ima preklapanja i nedostataka.

## Princip nove arhitekture

Razdvojiti dva pitanja koja su trenutno pomiješana:

1. **Da li tool radi?** → deterministički test, direktan poziv `handle_*`
   funkcije, bez `/api/chat`, bez LLM šuma. Mjeri kvalitet output-a.
2. **Da li Claude bira pravi tool?** → runtime test, `/api/chat`, mjeri
   tool-choice. LLM stochastika izolovana u jedan namjenski test.

## Plan koraka (jedno po jedno)

| # | Korak | Fajl(ovi) | Cilj | Effort |
|---|---|---|---|---|
| 1 | **Audit + rename** — popisati šta svaka skripta u `evals/` stvarno radi (deterministic vs runtime), preimenovati u prefiks: `sim_*` (no LLM) vs `runtime_*` (LLM). Odlučiti koji runner-i ostaju, koji se brišu/spajaju. | sve u `evals/` | jasna mental mapa | XS |
| 2 | **Deterministički overview test** — sibling postojećeg `visualize_parent_expansion.py`, ali zove `handle_category_overview(cat_id)` direktno. Validira: ≥3 djece, count>0, top3 prisutan. Bez `/api/chat`. | novi `sim_overview.py` | 100% deterministic baseline za novi tool | S |
| 3 | **Proširi `parent_eval_set.json` na ≥90% parenta** — iz `PARENT_CATEGORIES` u `app/tools.py` izvuci sve validne parente (≥2 aktivne djece) i auto-generiši set. | `parent_eval_set.json` (regen) | 90% coverage cilj | XS |
| 4 | **Deterministički search test** — direkt poziv `handle_search_products(query, category_id=...)`, ne `/api/chat`. Validira: top-k sadrži proizvod iz expected subtree-a. | novi `sim_search.py` | search relevance bez LLM šuma | M |
| 5 | **Runtime testovi → samo tool-choice signal** — postojeći `visualize_parent_runtime.py` zadržati, ali tretirati kao "da li Claude bira pravi tool", ne kao relevance test. Dodati `WRONG_TOOL_*` verdict (overview pozvan za kvalifikovani upit, search pozvan za bare parent). | `visualize_parent_runtime.py` (rename → `runtime_tool_choice.py`?) | LLM stochastiku izolovati u jedan test | S |
| 6 | **(Tek nakon 1-5) extract `_runtime_common.py`** — shared helper (load_tree, lookup, HTTP, healthz, HTML stil). | novi helper | DRY | S |

**Preporučen redoslijed:** 1 → 3 → 2 → 4 → 5 → 6. Prvo audit i proširenje eval
seta (cheap, oslobađa odluke), pa deterministički testovi (overview prvi jer
je nova feature-a), pa cleanup runtime semantike, pa DRY.

## Definicija "100% deterministic"

- Isti input → isti output, svaki put.
- Bez LLM-a u petlji za primarni correctness signal.
- LLM testovi postoje (`runtime_tool_choice.py`), ali mjere **tool-choice**,
  ne relevance.

## Definicija "≥90% coverage parenta"

- Trenutno: 15 upita u `parent_eval_set.json`.
- Cilj: pokriti ≥90% parent kategorija iz `PARENT_CATEGORIES` (parent sa ≥2
  aktivne djece) — auto-generisano iz `tools.py`, ne ručno održavano.
