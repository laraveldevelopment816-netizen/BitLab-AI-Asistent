# Eval ids & tags — implementacija plan

> Za drugu Claude code instancu. Pročitaj fajl, implementiraj sve, vrati listu od 9 ID-eva za NULL routing klaster + CLI primjere.

## 1. ID format

Sve entry-je u `evals/sets/categories_cold.json` i `evals/sets/products_cold.json` dobijaju polje `id` — 4-cifreni sekvencijalni broj kao string, bez prefix-a:

```json
{"id": "0001", "query": "Računari", "expect": {...}, "tags": [...]}
```

Categories i products svaki ima vlastiti counter od 0001. **Pozitivne i negativne ne razdvajamo namespace-om** — razdvajanje ide kroz tag.

## 2. Tag konvencija

- `expect-positive` — entry koji treba da prođe (query → očekivani routing).
- `expect-negative` — entry koji treba da padne kako je očekivano (npr. "namještaj" → escalate / out of scope).

Postojeći tagovi (`leaf`, `parent`, `auto-gen`) ostaju.

## 3. Auto-gen skripta (`scripts/gen_categories_eval.py`)

- Persistira postojeće ID-eve — ako entry sa istim `query` postoji, zadrži `id`.
- Novim entry-jima daje sljedeći broj nakon `max(existing_ids) + 1`.
- Idempotentna: re-pokretanje ne preuređuje order, ne mijenja postojeće ID-eve.
- Auto-gen entry-jima dodaje tag `expect-positive`.
- 10 manual negative entry-ja u istom fajlu dobijaju ID ručno i tag `expect-negative`.

## 4. Products set (`evals/sets/products_cold.json`)

21 entry, sav manual:

- Dodaj `id` (0001..0021).
- Razdvoji pozitivno/negativno sa `expect-positive` / `expect-negative` tagom.
- Ostali postojeći tagovi nedirnuti.

## 5. Alat — `run_categories.py` i `run_products.py`

Dodaj flag-ove (oba alata, isti API):

- `--ids 0007,0023,0091` — comma-separated lista.
- `--ids 0001-0009` — range, inclusive.
- `--tag expect-negative` — filter po tagu (može lista, AND presjek).
- `--query "string"` — ad-hoc upit van seta (već dogovoreno).
- Default (bez flag-ova) — cijeli set.

Kombinacija `--ids` + `--tag` → presjek.

## 6. HTML output

Leaderboard tabela: **prva kolona je `id`**. Ivan vidi failing ID-eve i kopira u `--ids` za sljedeći probe.

## 7. Acceptance — vrati Ivanu

1. **Lista od 9 ID-eva za NULL routing klaster** (cat ID-jevi su izvori iz `data/categories_new.json` po imenu): Skeneri, HDD storage, Graficke kartice, Projektori, Fiksna telefonija, Kućišta, Rezervni dijelovi elektronika, Optika interna, Produženje garancije.
2. CLI primjer za jedan: `python evals/run_categories.py --ids <skeneri-id> --label skeneri-baseline`.
3. CLI primjer za svih 9: `python evals/run_categories.py --ids <9-id-eva-comma> --label null-routing-baseline`.

## 8. Šta NE diraj

- Eval set semantiku (`query`, `expect.category_id`, `expect.tool`) — invariant.
- `app/system_prompts.py` — to ide sljedeća iteracija nakon što baseline od 9 testova padne kako je očekivano.
- Sve van `evals/`, `scripts/gen_*.py`, i set JSON-ova.
