# AGENTS.md — operativni vodič za Ralph na bitlab-ai-asistent

Ti si Claude Code agent koji radi u Ralph petlji. Svaka iteracija dobija čist kontekst — sve što ti treba o repou je ovdje + u `specs/` + u `ralph/IMPLEMENTATION_PLAN.md`. Drži ovaj fajl kratak; bloated AGENTS.md polutes svaku iteraciju.

## Repo u 4 rečenice

Python 3.11+ FastAPI app + voice/RAG agent za webshop.bitlab.rs. Trenutno na grani `claude/tdd-zero-base`: minimum `app/` (`main.py`, `agent.py` sa praznim system prompt-om i bez tools, `config.py`). Stara funkcionalna app u `bck/` — NIKAD ne reuse-uj wholesale; cherry-pick samo na zahtjev failing eval-a. Filozofija: failing eval → minimum dodaj → PASS → sljedeći eval.

## Komande

| Šta | Komanda |
|---|---|
| Server lokalno | `uvicorn app.main:app --port 7778` |
| Sve testove (default isključuje e2e/eval/anthropic_api) | `pytest -q` |
| Samo unit | `pytest -m unit -q` |
| Samo integration | `pytest -m integration -q` |
| E2E (Playwright, sporo) | `pytest -m e2e -q` |
| Real-LLM eval suite | `python -m evals.framework.runner --suite categories` |
| Eval dry (no entries, smoke) | `python -m evals.framework.runner --suite categories --limit 0` |
| Lint + format | `ruff format . && ruff check .` |
| Typecheck | `mypy app/ evals/framework/` |

## Backpressure (mora da prođe prije commit-a)

```bash
ruff format . && ruff check . && mypy app/ evals/framework/ && pytest -q
```

Ako ovo nije green, NE commit-uj. Fix prvo. Ako fix nije moguć u istom task-u, dodaj novi task u `ralph/IMPLEMENTATION_PLAN.md` (Next sekcija) i exit petlju.

## Git workflow

- Integraciona grana: `claude/tdd-zero-base`. Nikad ne push-uj na `main` ili `staging`.
- Feature grane: `feat/<scope>` (npr. `feat/ralph-categories-eval`). Branch off od `claude/tdd-zero-base`.
- Conventional Commits, BS/SR/CG jezik za poruke: `feat(scope): kratki opis`.
- PR: `gh pr create --base claude/tdd-zero-base --title "..." --body "..."`.

## Anthropic API budget

Pytest testovi MORAJU biti mock-ovani — `tests/conftest.py` ima `mock_anthropic` fixture. Real LLM samo u `evals/framework/runner.py` (eksplicitno pokretanje, ne u CI default-u). Nikad ne zovi `anthropic.Anthropic()` direktno iz test fajla.

## Pravila u petlji

1. **Don't assume not implemented** — `grep` prvo prije nego što tvrdiš da nešto nedostaje.
2. **One fix per loop** — jedan task iz `IMPLEMENTATION_PLAN.md`, ne dva paralelno.
3. **Eval set je invariant** — promijeni prompt/tool/dispatch, NE entry. Ako entry treba promjenu, prvo zapiši kao zaseban task.
4. **Minimum dodaj** — failing eval = jedini razlog za novi kod. Ako eval green, ne dodaj.
5. **Update plan kao side-effect commit-a** — Done task ide u Done sekciju sa commit SHA.

## Završetak petlje

Ako svi Now task-ovi prazni i sve faze acceptance ispunjeno: `touch ralph/STOP`, commit "chore(ralph): all phases complete", exit.
