# Repo inventory — po folderima (folder-group)

Komponentni pogled: [`repo-inventory-component-group.md`](repo-inventory-component-group.md). Osvježeno 2026-06-08 (doc reorg).
Statusi: `done` = završeno | `partial` = u toku | `reusable` = gotov alat | `dead` = arhiva/backup

---

### (root)

| Fajl | Šta je | Status |
|------|--------|--------|
| `CLAUDE.md` | Claude Code pravila za ovaj repo | `reusable` |
| `README.md` | Kako pokrenuti projekat i Ralph loop | `reusable` |
| `STATUS.md` | Kanban tabla sa aktivnim taskovima (eval regresija fix) | `partial` |
| `pyproject.toml` | Python dependencies i pytest/ruff konfiguracija | `reusable` |
| `repo-scan.md` | Auto-generisani dump cijelog repoa za dijeljenje s agentima | `reusable` |
| `scan.sh` | Skripta koja pravi taj dump | `reusable` |

> Doc reorg 2026-06-08: `PLAN`, `RESTORE`, `STATUS-HUMAN`, `EVAL_OPTIMIZACIJA`, `EVAL_REGRESIJA_iter17` premješteni u `docs/archives/`; `PLAN`+`RESTORE` spojeni u `docs/plans/baseline-i-restore.md`.

---

### app/

| Fajl | Šta je | Status |
|------|--------|--------|
| `__init__.py` | Verzija paketa (0.1.0) | `done` |
| `agent.py` | LLM loop — prima poruku, forsira tool call, vraća odgovor | `partial` |
| `config.py` | Sve env varijable i feature toggles (PWR/Anthropic, temp, enum) | `done` |
| `main.py` | FastAPI server, /api/chat endpoint, 429 mapiranje | `partial` |
| `tools.py` | Definicije alata (category_overview, search_products, respond_to_user) | `partial` |

---

### data/

| Fajl | Šta je | Status |
|------|--------|--------|
| `categories_new.json` | 229 KB — sve kategorije webshopa sa SEO metapodacima | `done` |
| `products.index.npz` | 7 MB — vektorski indeks za semantičku pretragu ~5 278 proizvoda | `done` |
| `products.meta.json` | 6 MB — metapodaci svih proizvoda (ime, cijena, stanje, kategorija) | `done` |

---

### docs/

| Fajl | Šta je | Status |
|------|--------|--------|
| `plans/akcioni-plan.md` | Strateški plan: Now (eval fix ≥95%), Next (RAG), Later (multi-tool) | `partial` |
| `plans/backlog.md` | Memorija/inbox; prioriteti prate board (P1 akcioni plan … P5 Ralph, P6 bck tool-ovi) | `partial` |
| `plans/baseline-i-restore.md` | Spoj PLAN+RESTORE: zero-base reset + izvlačenje iz bck/ → produkcija | `reusable` |
| `plans/lessons-learned.md` | Destilovane lekcije (L1 Ralph regresija, L2 verdict cache) | `done` |
| `plans/notes.md` | Sirovi inbox zapažanja | `partial` |
| `plans/repo-inventory-component-group.md` | Inventar po komponentama | `reusable` |
| `plans/repo-inventory-folder-group.md` | Ovaj fajl — inventar po folderima | `reusable` |
| `PROMPT-BEST-PRACTICES.md` | Analiza zašto model preskače tool callove i kako to arhitekturno riješiti | `done` |
| `eval-infra-changelog.md` | Dnevnik svih izmjena eval frameworka kroz dvije sesije | `done` |
| `eval-infra-review.md` | Šta je popravljeno, šta još čeka u eval infrastrukturi | `done` |
| `fb-funnel-progress.md` | Praćenje FB/LinkedIn B2B akvizicijskog eksperimenta | `partial` |
| `work/.../board.html` | Živi board za tekuću Now inicijativu | `partial` |
| `work/.../nalaz-fail-set-enum-temp.md` | Analiza zašto 7 od 15 fail case-ova ostaje — dvosmisleni, ne bug | `done` |
| `brainstorm/2026-06-07-plan-effort-burndown/` | Živa brainstorm sesija (log.md + board.html) | `partial` |
| `archives/` | Outdated/završeni (STATUS-HUMAN, PLAN, RESTORE, EVAL_*, repo-inventory-en, repo-map) | `dead` |

---

### evals/framework/

| Fajl | Šta je | Status |
|------|--------|--------|
| `__init__.py` | Prazni marker fajlovi | `done` |
| `budget.py` | Broji PWR pozive u zadnjih 5h, pauzira runner na 65% od 80 limita | `reusable` |
| `cache.py` | SHA-256 cache verdikta — ne poziva PWR ponovo za iste ulaze | `reusable` |
| `client.py` | HTTP klijent za /api/chat, pretvara 429 u RateLimitDetected | `reusable` |
| `errors.py` | Jedna custom exception: RateLimitDetected | `done` |
| `judge.py` | Ocjenjuje tool call bez LLM-a — čisti parser, deterministički | `reusable` |
| `loader.py` | Čita .jsonl eval setove, validira polja, preskače komentare | `reusable` |
| `reporter.py` | Piše verdikate u JSONL, pravi HTML dashboard, štampa terminal summary | `reusable` |
| `runner.py` | Srce evala — orkestrira sve module, resume/checkpoint, exit kodovi 0–4 | `reusable` |
| `sampler.py` | Smanjuje 250 case-ova na ~30 za brzo dev testiranje, stratikovano | `reusable` |
| `types.py` | TypedDict sheme za cijeli framework (EvalEntry, Verdict, ToolCall...) | `reusable` |

---

### evals/sets/

| Fajl | Šta je | Status |
|------|--------|--------|
| `categories.jsonl` | 250 case-ova, auto-generisano iz categories_new.json | `reusable` |
| `categories_acpt_fails.jsonl` | 15 FAIL + 8 negativnih — jeftini brzi gate pred punim runom | `partial` |
| `categories_dev.jsonl` | 29 regresija iz iter17 — za brzo tweakovanje prompta | `reusable` |
| `categories_leaf_tune.jsonl` | 15 routing FAILova + 6 halucincija iz 94% acceptance runa — aktivan tune | `partial` |
| `categories_manual.jsonl` | Ručno pisani negativni slučajevi — nikad auto-gen, stalan SSOT | `reusable` |

---

### public/

| Fajl | Šta je | Status |
|------|--------|--------|
| `voice.html` | Voice UI — animirani orb, VAD, STT/TTS pipeline | `done` |
| `widget.html` | Demo webshop stranica za testiranje embeddanog widgeta | `done` |
| `widget.js` | Embeddable chat widget koji se ubacuje jednim script tagom | `partial` |
| `assets/PITCH-BRIEF.md` | Brief za dizajnera pitch decka sa ROI kalkulacijom i flow skriptom | `done` |
| `assets/favicon.ico` | Favicon | `done` |
| `assets/img/bitlabLogo.png` | BitLab logo | `done` |
| `assets/...Pitch v2.pdf` | Engineering pitch prezentacija v2, PDF | `done` |
| `assets/...Asistent.pdf` | Originalni pitch deck, PDF | `done` |
| `assets/...Asistent.pptx` | Editabilna PowerPoint verzija pitch decka | `done` |

---

### ralph/

| Fajl | Šta je | Status |
|------|--------|--------|
| `AGENTS.md` | Pravila za Ralph agenta — šta smije, šta ne, kako koristi git i PWR | `reusable` |
| `IMPLEMENTATION_PLAN.md` | Ralph-ov živi kanban — Now/Next/Later + per-iter PASS/FAIL historija | `partial` |
| `PROMPT_build.md` | Prompt koji ralph.sh šalje Claudeu u build modu (7 faza) | `reusable` |
| `PROMPT_plan.md` | Prompt za plan mod — gap analiza, bez implementacije | `reusable` |
| `estimate_reset.py` | Računa kad se PWR 5h window resetuje za PAUSE marker | `reusable` |
| `ralph-plan.sh` | Pokreće ralph.sh u plan modu (MAX_ITERS=1) | `reusable` |
| `ralph.sh` | Glavni loop — iterira Claude, prati STOP/PAUSE, loguje | `reusable` |
| `status.sh` | Terminal dashboard — Ralph status, PASS rate, zadnji commiti | `reusable` |
| `wait_pause.py` | Čeka da PAUSE marker istekne ili fajl nestane | `reusable` |
| `logs/iter29-rezum.log` | Log kratkog rezum runa — 3 cache HIT, sve PASS | `dead` |
| `logs/ralph-20260525-071044.log` | Ralph sesija 25.05 07:10 — iter1 build mod | `dead` |
| `logs/ralph-20260525-075845.log` | Ralph sesija 25.05 07:58 — iter11, 82.7% PASS | `dead` |
| `logs/ralph-20260525-183906.log` | Ralph sesija 25.05 18:39 — plan mod, commit 40e330b | `dead` |

---

### scripts/

| Fajl | Šta je | Status |
|------|--------|--------|
| `__init__.py` | Marker | `done` |
| `gen_acpt_fails.py` | Pravi categories_acpt_fails.jsonl iz zadnjeg acceptance runa | `reusable` |
| `gen_categories_eval.py` | Regeneriše categories.jsonl iz data/categories_new.json | `reusable` |
| `gen_dev_sample.py` | Pravi categories_dev.jsonl — regresije iter8→iter17 | `reusable` |
| `run_acceptance.sh` | Batch runner — 250 case-ova u grupama od ~80, spava 5h između | `reusable` |
| `smoke.py` | Brza ručna provjera — pošalje par upita, ispiše koji tool je pozvan | `reusable` |

---

### specs/

| Fajl | Šta je | Status |
|------|--------|--------|
| `categories.md` | Spec za Fazu 1 — pravila rutiranja, eval shema, acceptance ≥95% | `partial` |
| `cross-reference.md` | Placeholder spec za Fazu 3 — multi-tool upiti (kat+cijena+brand) | `partial` |
| `products.md` | Placeholder spec za Fazu 2 — RAG pretraga proizvoda | `partial` |

---

### tests/

| Fajl | Šta je | Status |
|------|--------|--------|
| `conftest.py` | Mock fixture-i za Anthropic i PWR — nema pravih API poziva u testovima | `reusable` |
| `e2e/test_smoke.py` | Provjera da Playwright može da se importuje (skip bez e2e markera) | `partial` |
| `integration/test_eval_runner_budget.py` | Runner pauzira s exit 3 kad budget preskoči prag | `done` |
| `integration/test_eval_runner_cache.py` | Cache hit/miss, limit/dry-run, sample mod, fail-fast | `done` |
| `integration/test_eval_runner_resume.py` | Resume s checkpointa, append u JSONL, mode-mismatch abort (exit 4) | `done` |
| `integration/test_main_rate_limit.py` | FastAPI vraća 429, ne 500, za RateLimitError s oba backenda | `done` |
| `integration/test_runner_writes_pause_marker.py` | PAUSE marker se piše s validnim `until=<epoch>` na exit 3 | `done` |
| `integration/test_smoke.py` | /healthz, PWR vs Anthropic routing, prazna poruka → 422 | `done` |
| `integration/test_status_script.py` | status.sh vraća exit 0 i ispisuje sve tražene sekcije dashboarda | `done` |
| `integration/test_tool_dispatch.py` | Oba tool-a se ispravno dispatčuju kroz oba LLM backenda | `done` |
| `regression/test_smoke.py` | Placeholder — provjera da pytest pokupi regression marker | `partial` |
| `unit/test_eval_budget.py` | record_call, count_calls_last_5h, should_pause threshold | `done` |
| `unit/test_eval_cache.py` | Hash determinizam, get/put roundtrip, stats, sampler edge case-ovi | `done` |
| `unit/test_eval_client.py` | 429 → RateLimitDetected, ostalo → httpx greška, 2xx → JSON | `done` |
| `unit/test_eval_errors.py` | RateLimitDetected je Exception i čuva poruku | `done` |
| `unit/test_eval_framework.py` | Judge logika, loader validacija, reporter output | `done` |
| `unit/test_gen_categories_eval.py` | Leaf vs parent pravila, schema, determinizam, loader kompatibilnost | `done` |
| `unit/test_ralph_pause.py` | PAUSE marker parsing, poll loop, reset epoch estimacija | `done` |
| `unit/test_ralph_prompt.py` | PROMPT_build.md i AGENTS.md sadrže sve obavezne guardrail sekcije | `done` |
| `unit/test_smoke.py` | App se importuje, run_agent postoji, settings su učitani | `done` |
| `unit/test_system_prompt.py` | SYSTEM_PROMPT_V1 nije prazan i prosljeđuje se ispravno oba backenda | `done` |

---

### var/

| Fajl | Šta je | Status |
|------|--------|--------|
| `bitlab.db` | SQLite 1.7 MB — runtime baza, historija razgovora i sesija | `partial` |

---

### bck/

| Fajl | Šta je | Status |
|------|--------|--------|
| `bck/ (cijeli folder)` | 254 fajla — kompletan stari kod arhiviran prije TDD reseta (app, dashboard, data, deploy, docs, evals, n8n, scripts, tests) | `dead` |
