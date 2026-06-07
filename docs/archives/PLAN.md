# PLAN — TDD eval-driven reset (2026-05-23)

## Cilj
Krenuti od nule: prazan system prompt, nikakvi tools, nikakva poslovna logika.
Eval drive — failing eval → minimum dodaj → PASS → sljedeći eval. Branch: `claude/tdd-zero-base`.

## Pristup

1. Sva poslovna logika iz `app/` ide u `bck/app/`: `agent.py`, `system_prompts.py`, `tools.py`,
   `categories.py`, `brands.py`, `rag.py`, `faq.py`, `contacts.py`, `email_poller.py`, `server/`, `storage/`.
2. U `app/` ostaje samo minimum za boot:
   - `main.py` — FastAPI, `/healthz`, `/api/chat`, static mount `/public`.
   - `config.py` — `ANTHROPIC_API_KEY`, `chat_model`.
   - `agent.py` (novi, tanki) — `run_agent(messages)` → Claude poziv, system="", bez tools.
3. `public/widget.html` + `widget.js` ostaju kako jesu (frontend, no business logic).
4. `evals/sets/categories_cold.json` → `bck/evals/` (sklanjamo iz mape).
   Novi `evals/sets/cold.json` ima **jedan entry**: "Mobiteli" → `category_overview(151)`.
5. Root markdown fajlovi (EVAL-*, TEST-*, SSOT-*, CATEGORIES-test-plan, README-STANDARD) → `bck/docs/`.
6. `dashboard/`, `n8n/`, `deploy/`, `var/` → `bck/` (nije potrebno za prikaz + pokretanje).
7. `bck/` u `.gitignore` (može se vratiti kroz `git log`); committujemo samo aktivnu strukturu.

## Workflow nakon reseta

- `python evals/run_categories.py` → očekivani FAIL (nema tools, nema prompta).
- Dodaj **najmanje moguće** da prođe prvi entry (npr. samo `category_overview` tool definicija, parent_id=151 hardcode).
- Re-run → PASS.
- Sljedeći entry tek nakon zelenog na prethodnom.

## Pravila

- Ni jedan red prompt-a, tool flag, ni dispatch grana koja nije eksplicitno tražena od failing eval-a.
- Jedan fix u jednom trenutku ([[feedback-one-fix-at-a-time]]).
- Eval set invariant ([[feedback-test-case-invariant]]) — entry se ne pomjera da bi prošlo; mijenjamo sistem.

## Prvi konkretni task

Move sve poslovne fajlove u `bck/`, izdvojiti u rootu samo minimum za:
(a) FastAPI boot, (b) widget učitavanje, (c) `/api/chat` koji prosljeđuje user message Claude-u sa **praznim** system prompt-om i **bez** tools-a. Cilj: server starta, widget se prikazuje, prvi eval pada predvidljivo.
