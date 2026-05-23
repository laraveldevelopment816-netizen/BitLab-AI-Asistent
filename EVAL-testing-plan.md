# Testing plan — eval ID/tag refactor

> Unit + integration testovi za novu funkcionalnost dodatu u prethodnom koraku ([EVAL-ids-tags-plan.md](./EVAL-ids-tags-plan.md)). Cilj: alat za testiranje sam pod test-om — bez toga signal iz alata = neizvjestan.

## Datoteke pod test-om (po prioritetu)

1. `evals/_cli_filters.py` — čista logika (parser + filter), **top priority**.
2. `scripts/gen_categories_eval.py` — auto-gen sa persist ID logikom.
3. JSON integritet — `evals/sets/{categories,products}_cold.json` šema.
4. `evals/run_categories.py` / `evals/run_products.py` — CLI smoke (zahtjeva server stub).

## 1. `parse_ids_spec()` — `tests/test_cli_filters.py::test_parse_ids_spec_*`

- Single — `"0007"` → `{"0007"}`.
- Comma lista — `"0001,0023,0091"` → 3 elementa.
- Range inclusive — `"0001-0009"` → 9 elemenata.
- Mixed — `"0001-0003,0050"` → 4 elementa.
- Padding — `"7"` → `{"0007"}`.
- Whitespace — `"0001, 0023"` → 2 elementa.
- Prazno — `""` → `set()`.
- Range jedan — `"0005-0005"` → `{"0005"}`.
- Reverse range — `"0009-0001"` → trenutno prazno (`range(9,2)` empty); test potvrđuje i odlučuje da li OK ili treba exception.
- Invalid token — `"abcd"` → trenutno fallback (`{"abcd"}`); test potvrđuje i odlučuje.

## 2. `apply_filters()` — `tests/test_cli_filters.py::test_apply_filters_*`

Fixture: minimalan set od 5 entry-ja sa različitim tagovima i ID-jevima.

- No flags → unchanged queries.
- `args.query="x"` → 1 ADHOC entry sa `id="ADHOC"`, ostalo ignorisano.
- `args.ids="0001"` → 1 entry.
- `args.tag=["expect-positive"]` → svi pozitivni.
- `args.ids="0001,0002"` + `args.tag=["expect-positive"]` → AND presjek.
- `args.tag=["expect-negative", "not_in_catalog"]` → AND između tag-ova.
- `args.ids="9999"` (nepostojeći) → prazna lista (alat sam handluje grešku).

## 3. JSON integritet — `tests/test_eval_sets_schema.py`

Za oba seta:

- Svaki entry ima `id` field, regex `^\d{4}$`.
- ID-jevi unique (`len(ids) == len(set(ids))`).
- Svaki entry ima **tačno jedan** od `expect-positive` / `expect-negative` (XOR).
- Pozitivni entry-ji imaju non-empty `expect.category_id`.
- Negativni entry-ji imaju `expect.tool == None` i `expect.failure_reason`.
- `id` je prvi ključ u JSON objektu (provjera: `list(entry.keys())[0] == "id"`).

## 4. Auto-gen idempotency — `tests/test_gen_categories_eval.py`

- Dvostruko pokretanje skripte → output identican (MD5 hash; druga instanca već potvrdila ručno).
- Postojeći ID-jevi nikad ne mijenjaju vrijednost (mutacijski test: dodaj kategoriju u temp CSV → re-run → svi postojeći ID-jevi sačuvani).
- Novi entry dobija `max(existing_ids) + 1`.
- **Homonimi:** Ventilatori, Eksterni HDD, USB uređaji imaju različite ID-eve — persist key je `(query, cat_id)`, ne samo `query`. Provjeri sa fixture-om koji simulira homonim.

## 5. NULL routing klaster — sanity (uključeno u JSON schema test)

Druga instanca već identifikovala ID-eve. Provjera da JSON sadrži:

| ID | Upit | Expected cat |
|---|---|---|
| 0007 | Produženje garancije | 101 |
| 0014 | HDD storage | 114 |
| 0016 | Optika interna | 116 |
| 0017 | Graficke kartice | 117 |
| 0018 | Kućišta | 118 |
| 0028 | Skeneri | 131 |
| 0038 | Projektori | 149 |
| 0041 | Fiksna telefonija | 154 |
| 0050 | Rezervni dijelovi elektronika | 167 |

## 6. Acceptance — prije baseline run-a

Sekcije 1–4 **moraju proći** prije nego što alat ide u probe. Manual smoke (Ivan pokreće alat ručno) zamjenjuje CLI smoke testove — nema potrebe za mock infrastrukturom u suite-u.

Ako bilo koji test pada — alat se ne smije koristiti za baseline (false signal scenarij iz [SSOT-eval-delta-analysis.md](./SSOT-eval-delta-analysis.md)).

## 7. Pokretanje

```bash
pytest tests/test_cli_filters.py tests/test_eval_sets_schema.py \
       tests/test_gen_categories_eval.py -v
```

## 8. Prompt za drugu instancu

Pročitaj ovaj fajl i implementiraj sve testove. Cilj: `pytest` zelen prije bilo kakvog `--ids` probe-a alata. Ne diraj `app/system_prompts.py` (sljedeća iteracija). Pokriva: parser, filter, JSON schema, idempotency. **NEMA** automatizovanog CLI smoke testa — to je manual run kad treba.
