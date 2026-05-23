# Ralph plan mode — gap analysis i update IMPLEMENTATION_PLAN.md

NE implementiraj NIŠTA. Tvoj jedini posao je da ažuriraš `ralph/IMPLEMENTATION_PLAN.md`. Nikakav app kod, nikakav test, nikakav eval entry.

## Faza 0 — Orient

Pročitaj:
1. `ralph/AGENTS.md` — kontekst repoa.
2. Svi `specs/*.md` — šta sistem treba da radi.
3. Trenutni `ralph/IMPLEMENTATION_PLAN.md` — Now/Next/Later/Done.
4. Postojeći kod (`app/`, `evals/framework/`, `evals/sets/`).
5. Posljednji eval run: `ls -t evals/runs/*.jsonl 2>/dev/null | head -1` — koje entry pada?

## Faza 1 — Gap analysis

Za svaki spec:
- Šta je već implementirano u kodu? (`grep`, `ls app/`)
- Šta eval pokazuje da NE radi? (parse JSONL, filtriraj `verdict.overall != PASS`)
- Šta spec traži a niti kod niti eval ne pokriva?

Izlistaj gap-ove u glavi (ne u plan fajlu).

## Faza 2 — Update plan

Strukturiraj `ralph/IMPLEMENTATION_PLAN.md`:

- **Now** (3-5 task-ova): redoslijed izvršenja, top = sljedeći. Svaki task u Now mora biti izvršiv u jednom Ralph build ciklusu (1-2h rada).
- **Next** (5-10 task-ova): vidljiv horizont, narednih nekoliko ciklusa.
- **Later** (sve ostalo): ideje, low priority, parking.
- **Done** (chronološki, najnovije gore): sa datumom + commit SHA + 1-liner šta je urađeno.

Svaki task mora imati:
- **Naslov** (imperativ): "Dodaj `search_products` tool dispatch u `app/agent.py`".
- **Acceptance** (mjerno): "eval suite categories PASS rate ≥80%, integration test prolazi".
- **Spec referenca**: "`specs/categories.md` §3".

## Faza 3 — Commit (ako je plan stvarno izmijenjen)

```bash
git add ralph/IMPLEMENTATION_PLAN.md
git commit -m "chore(ralph): update plan — <kratki why, npr. 'pojavila se 3 nova faila u eval-u'>"
git push
```

Exit. Build petlja (`bash ralph/ralph.sh`) sljedeća iteracija preuzima top Now task.

## Anti-patterns

- Nemoj implementirati ništa — čak ni "trivial" stvari.
- Nemoj raditi gigant plan sa 50 task-ova — Now mora ostati 3-5.
- Nemoj kopirati cijeli spec u plan — referenca je dovoljna.
- Nemoj prepravljati Done task-ove. Done je arhivski.
- Nemoj komitovati ako plan zaista nije izmijenjen.
