# AGENTS.md — operativni vodič za Ralph na bitlab-ai-asistent

Ti si Claude Code agent koji radi u Ralph petlji. Svaka iteracija dobija čist kontekst — sve što ti treba o repou je ovdje + u `specs/` + u `ralph/IMPLEMENTATION_PLAN.md`. Drži ovaj fajl kratak; bloated AGENTS.md polutes svaku iteraciju.

## Repo u 4 rečenice

Python 3.11+ FastAPI app + voice/RAG agent za webshop.bitlab.rs. Trenutno na grani `claude/tdd-zero-base` (integraciona) ili feature grani off od nje: minimum `app/` (`main.py`, `agent.py` sa PWR/Anthropic dispatch i bez tools, `config.py`). Stari kod dostupan u git history (`git show <sha>:path`) — NIKAD ne reuse-uj wholesale; cherry-pick samo na zahtjev failing eval-a. Filozofija: failing eval → minimum dodaj → PASS → sljedeći eval.

## Komande

| Šta | Komanda |
|---|---|
| Server lokalno | `uvicorn app.main:app --port 7778` |
| Sve testove (default isključuje e2e/eval/anthropic_api) | `pytest -q` |
| Samo unit | `pytest -m unit -q` |
| Samo integration | `pytest -m integration -q` |
| E2E (Playwright, sporo) | `pytest -m e2e -q` |
| Real-LLM eval (25 entry-ja, max po sesiji) | `python -m evals.framework.runner --suite categories --limit 25` |
| Eval resume (nastavak nakon rate limit) | `python -m evals.framework.runner --suite categories --resume --limit 25` |
| Eval dry (no entries, smoke) | `python -m evals.framework.runner --suite categories --limit 0` |
| Lint + format | `ruff format . && ruff check .` |
| Typecheck | `mypy app/ evals/framework/` |

## PWR sesija management (IMPERATIV)

Claude pretplata ima limit poruka po sesiji. 250 eval entry-ja = 250 poziva = više sesija.

**Pravila:**

1. **Max 25 eval poziva po iteraciji petlje** — uvijek koristi `--limit 25`. Za brzi
   fail pattern check, `--limit 10` je dovoljno.

2. **Provjeri state fajl prije pokretanja eval-a:**
   ```bash
   cat ralph/session-state.json 2>/dev/null || echo "nema state-a, počni od 0"
   ```
   Ako postoji sa `"reason": "rate_limit"` i isti suite — dodaj `--resume`.

3. **Rate limit = auto-stop** — runner automatski:
   - Bilježi gdje je stao u `ralph/session-state.json`
   - Kreira `ralph/STOP` marker (petlja se zaustavi)
   - Ispiše tačnu komandu za nastavak u konzoli

4. **Nakon reseta sesije** (sesija se resetuje po UTC rasporedu, pitaj korisnika kad):
   ```bash
   rm ralph/STOP
   python -m evals.framework.runner --suite categories --resume --limit 25 --label <isti-label>
   ```

5. **State fajl se briše automatski** kad run prođe bez rate limita — ne brišeš ručno.

## Backpressure (mora da prođe prije commit-a)

```bash
ruff format . && ruff check . && mypy app/ evals/framework/ && pytest -q
```

Ako ovo nije green, NE commit-uj. Fix prvo. Ako fix nije moguć u istom task-u, dodaj novi task u `ralph/IMPLEMENTATION_PLAN.md` (Next sekcija) i exit petlju.

## Git workflow

- Integraciona grana: `claude/tdd-zero-base`. Nikad ne push-uj na `main` ili `staging`.
- **Jedna feature grana za cijeli eksperiment**: ostani na trenutnoj grani (provjeri `git branch --show-current` — npr. `feat/ralph-categories-eval`). NE pravi nove grane za Faze 2 i 3 — sve task-ove svih faza commit-uješ na istu granu. Korisnik na kraju otvara JEDAN PR ka `claude/tdd-zero-base`.
- Conventional Commits, BS/SR/CG jezik: `feat(scope): kratki opis`.
- PR: `gh` CLI nije instaliran u WSL-u — korisnik otvara PR ručno preko GitHub URL-a kad eksperiment kompletira. Ne pokušavaj `gh pr create`.

## LLM backend dispatch (IMPERATIV — memorija `llm_backend_pwr_imperative`)

Svi LLM pozivi MORAJU kroz `app/agent.py:run_agent` dispatch, koji bira backend po `settings.llm_backend`:

- **`LLM_BACKEND=pwr` + `PWR_API_KEY` set** (default po `.env`): `_run_pwr` koristi `openai` SDK ka lokalnom PlaywrightRouter (`http://127.0.0.1:8765/v1`). Troši kredite Claude pretplate, NE plaćeni Anthropic API.
- **`LLM_BACKEND=anthropic` ili PWR ne setovan**: `_run_anthropic` direktan Anthropic API. Fallback, ne preporučeno za produkciju.

**NIKAD `anthropic.Anthropic().messages.create(...)` direktno iz drugog koda.** Sve ide kroz `run_agent` ili `_get_anthropic_client()` / `_get_pwr_client()` helper-e.

**Kad dodaješ tools (Faza 1+)**: mora u OBA runnera. Anthropic shape u `_run_anthropic`, OpenAI shape (derivacija) u `_run_pwr`. Pogledaj stari kod referencu: `git show 3d4bc87:app/agent.py` (`ALL_TOOLS` + `ALL_TOOLS_OPENAI_SHAPE`).

## Anthropic API budget (memorija `anthropic_budget`)

Pytest invariant: `tests/conftest.py` `mock_llm` fixture mock-uje OBA klijenta (anthropic + pwr). Nikad ne zovi ni pwr ni anthropic stvarno iz pytest-a — koristi `mock_llm` + `force_backend_pwr` ili `force_backend_anthropic` fixture-e. Real LLM samo u `evals/framework/runner.py` (manuelno pokretanje ili nightly cron, ne u default CI).

## Pravila u petlji

1. **Don't assume not implemented** — `grep` prvo prije nego što tvrdiš da nešto nedostaje.
2. **One fix per loop** — jedan task iz `IMPLEMENTATION_PLAN.md`, ne dva paralelno.
3. **Eval set je invariant** — promijeni prompt/tool/dispatch, NE entry. Ako entry treba promjenu, prvo zapiši kao zaseban task.
4. **Minimum dodaj** — failing eval = jedini razlog za novi kod. Ako eval green, ne dodaj.
5. **Update plan kao side-effect commit-a** — Done task ide u Done sekciju sa commit SHA.

## Završetak petlje

Ako svi Now task-ovi prazni i sve faze acceptance ispunjeno: `touch ralph/STOP`, commit "chore(ralph): all phases complete", exit.
