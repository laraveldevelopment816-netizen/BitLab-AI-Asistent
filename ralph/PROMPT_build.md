# Ralph build mode — implementiraj jedan task iz plana

Ovo je tvoj jedini prompt. Tvoj kontekst je čist — sve što treba je u fajlovima na disku.

## Faza 0 — Orient

Pročitaj u ovom redoslijedu:
1. `ralph/AGENTS.md` — kako se radi na repou (komande, backpressure, git).
2. `ralph/IMPLEMENTATION_PLAN.md` — Now sekcija, top task.
3. Spec relevantan za task (npr. `specs/categories.md`).
4. Postojeći kod (`app/`, `evals/framework/`) koji task dira — `grep` prvo.

## Faza 1 — Pick top Now task

Uzmi PRVI nezavršen task iz Now sekcije. Ne preskači, ne biraj po preferenci. Ako je Now prazan, pokreni `bash ralph/ralph-plan.sh` (plan mode update) i exit — sljedeća iteracija dobija nove task-ove.

## Faza 2 — Implement minimum

Dodaj NAJMANJE moguće da prođe acceptance criteria task-a. Ne predviđaj sljedeće task-ove. Ne refaktoriši uz put. Ne dodaj feature koji acceptance ne traži.

## Faza 3 — Backpressure

```bash
ruff format . && ruff check . && mypy app/ evals/framework/ && pytest -q
```

Ako fail — fix. Ako fix izlazi iz scope-a task-a, dodaj novi task u Next sekciju i exit (ne nastavljaj uz blocked task).

## Faza 4 — Eval (ako task ima eval acceptance)

Pokreni: `python -m evals.framework.runner --suite <suite> --limit 5 --fail-fast`. Ako acceptance nije zadovoljeno — fix prompt/tool/dispatch (NE eval entry).

## Faza 5 — Commit + push

Branch (ako nisi već na feature grani):
```bash
git checkout -b feat/<scope>
```

Commit + push:
```bash
git add -p   # ili specifične fajlove; nikad git add -A
git commit -m "feat(scope): kratki opis"
git push -u origin HEAD
```

## Faza 6 — Update plan

U `ralph/IMPLEMENTATION_PLAN.md`:
- Premjesti završeni task iz Now u Done sa datumom + commit SHA (`git rev-parse --short HEAD`).
- Ako su otkriveni novi task-ovi (fix-up, refaktor, blocker), dodaj u Next.

## Faza 7 — PR i exit

Ako feature grana ima ≥1 commit i fazni cilj je dostignut:
```bash
gh pr create --base claude/tdd-zero-base \
  --title "feat(scope): ..." \
  --body "$(head -30 ralph/IMPLEMENTATION_PLAN.md)"
```

Exit. Petlja restartuje sa svježim kontekstom.

## 999 — Guardrails (kritični)

- **999.1** Nemoj pretpostaviti da nešto nije implementirano. `grep -r 'symbol' app/ evals/` prvo.
- **999.2** Nemoj dirati `evals/sets/*.jsonl` entries. Eval je invariant.
- **999.3** Nemoj zvati pravi Anthropic API iz pytest. `mock_anthropic` fixture.
- **999.4** Nemoj push-ovati na `main` ili `staging`. PR baza je `claude/tdd-zero-base`.
- **999.5** Nemoj raditi 2+ task-a u jednoj iteraciji. Jedan in, jedan out.
- **999.6** Nemoj pisati novi kod ako acceptance prolazi sa postojećim. YAGNI.
- **999.7** Jezik commit poruka i komentara: BS/SR/CG. Identifikatori: engleski.
- **999.8** Ako ne znaš šta dalje — STOP, zapiši dilemu u `ralph/IMPLEMENTATION_PLAN.md` (Next) umjesto guess-a.
- **999.9** LLM pozivi MORAJU kroz `app/agent.py:run_agent` dispatch (PWR-first, Anthropic fallback). Nikad `anthropic.Anthropic().messages.create()` direktno iz drugog koda. Vidi `ralph/AGENTS.md` § LLM backend dispatch + memoriju `llm_backend_pwr_imperative`.
- **999.10** Tools (Faza 1+) idu u OBA runnera (`_run_anthropic` Anthropic shape + `_run_pwr` OpenAI shape, derivacija). Pytest sa `mock_llm` + `force_backend_pwr` ILI `force_backend_anthropic` fixture-om. Stari kod referenca: `git show 3d4bc87:app/agent.py`.
