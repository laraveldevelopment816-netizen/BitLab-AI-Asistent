# BitLab AI Asistent

## Brzi start

```bash
git clone https://github.com/laraveldevelopment816-netizen/BitLab-AI-Asistent.git
cd BitLab-AI-Asistent
python3 -m venv .venv && source .venv/bin/activate
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu
cp .env.example .env && nano .env   # popuni ANTHROPIC_API_KEY, DASHBOARD_API_KEY
python scripts/embed_products.py    # ~5min, jednokratno
python scripts/build_categories.py
python scripts/init_db.py
uvicorn app.main:app --reload
```

Dashboard (drugi terminal):
```bash
cd dashboard && pnpm install && pnpm dev
```

Otvori http://localhost:8000 (chat) i http://localhost:5173/admin/ (dashboard).

Detalji: [`docs/getting-started.md`](./docs/getting-started.md)

## Ralph + testovi (TDD eksperiment, grana `claude/tdd-zero-base`)

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" --extra-index-url https://download.pytorch.org/whl/cpu

# Backpressure (mora green prije commit-a)
ruff format . && ruff check . && mypy app/ evals/framework/ && pytest -q

# Quick dashboard (proces, log, posljednji commit + eval rate)
bash ralph/status.sh
tail -F $(ls -t ralph/logs/*.log | head -1)   # uživo praćenje najnovijeg loga

# Ralph petlja — autonomic TDD na trenutnoj feature grani
uvicorn app.main:app --port 7778 &
bash ralph/ralph.sh                                  # foreground, default MAX_ITERS=100, pause auto na 65%
nohup bash ralph/ralph.sh >/dev/null 2>&1 & disown   # background — preživi terminal/Claude Code restart (gasi se samo sa touch STOP)
touch ralph/STOP                                     # cooperative exit (čeka kraj tekuće iter ili wait_pause poll)
touch ralph/PAUSE                                    # cooperative pauza (rm za nastavak)
echo "until=$(date -d '+1h' +%s)" > ralph/PAUSE      # auto-resume nakon 1h

# Eval suite (manualno, ne u CI default-u — troši PWR sesiju)
python -m evals.framework.runner --suite categories --mode sample
python -m evals.framework.runner --suite categories --resume <label>  # nastavi sa checkpoint-a

# Ručna ekstra Ralph iteracija (stop + manual run + restart, ~2-3 min prekid)
touch ralph/STOP                                                          # Ralph završi tekuću iter, exit
cat ralph/PROMPT_build.md | claude --print --dangerously-skip-permissions # jedan dodatni iter kroz Claude
rm ralph/STOP && bash ralph/ralph.sh                                      # restart loop
```

Detalji: [`docs/eval-infra-changelog.md`](./docs/eval-infra-changelog.md), [`ralph/AGENTS.md`](./ralph/AGENTS.md).

## Pun acceptance eval (categories, 250)

`scripts/run_acceptance.sh` prolazi kroz cijeli set u serijama od ~80 case-ova (≈80% jedne PWR sesije), sačeka 5h da se sesija resetuje i nastavi odakle je stao — dok ne odradi svih 250. Sve ide u jedan fajl `evals/runs/categories-acpt.jsonl`. Pošto traje preko više 5h prozora, pusti ga pod nohup:

```bash
nohup bash scripts/run_acceptance.sh > evals/runs/acpt-run.log 2>&1 & disown   # pusti i zaboravi
tail -f evals/runs/categories-acpt.jsonl                                       # napredak: jedan red = jedan case
tail -f evals/runs/acpt-run.log                                                # log petlje: prolazi i pauze
```

Server mora biti gore prije pokretanja: `.venv/bin/uvicorn app.main:app --port 7778`.

**Zašto 250 a ne 255:** `data/categories_new.json` ima 255 kategorija, ali generator (`scripts/gen_categories_eval.py`) preskače 5 parenata sa tačno 1 djetetom — spec (`specs/categories.md §2`) taj slučaj ne pokriva: *Satovi, Memorijske kartice, Aktiva, Pročišćivači zraka i filteri, Putni program*. Ostaje 220 leaf (→ `search_products`) + 30 parent s ≥2 djece (→ `category_overview`) = 250.
