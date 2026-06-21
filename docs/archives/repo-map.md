# Repo Map

### (root)

| File | Description |
|------|-------------|
| `CLAUDE.md` | Project-level Claude Code instructions that identify the deployment URLs and import shared bitlab-standards rules. |
| `EVAL_OPTIMIZACIJA.md` | Design document (2026-05-24) proposing five strategies to reduce costly PWR eval calls (verdict cache, tiered eval, prompt caching, concurrency) plus a review of the reactive rate-limit checkpoint implementation on the eval-fix branch. |
| `EVAL_REGRESIJA_iter17.md` | Post-mortem analysis of the iter17 prompt regression showing that adding Groups A+B rules dropped routing accuracy from 84.4% to 79.2% by causing the model to skip tool calls and hallucinate a product catalog instead. |
| `PLAN.md` | TDD zero-base reset plan that describes moving all business logic to bck/, leaving only a minimal FastAPI boot, and driving every new addition with a failing eval entry. |
| `README.md` | Developer quick-start guide covering local setup, Ralph autonomous TDD loop commands, and the chunked 250-entry acceptance eval runner. |
| `RESTORE.md` | Step-by-step recipe for restoring the fully functional pre-reset application from the bck/ directory, including a list of all tracked and untracked files that were moved there. |
| `STATUS-HUMAN.md` | Plain-language translation of STATUS.md explaining the routing eval problem, the iter17 regression, and each Kanban card in natural prose for quick human orientation. |
| `STATUS.md` | Formal Kanban board (machine-readable with IDs) tracking the active prompt-fix and acceptance tasks for the categories routing eval, including current doing/todo/done state and known limitations. |
| `pyproject.toml` | Python project manifest defining dependencies (FastAPI, Anthropic, OpenAI, sentence-transformers, torch CPU), dev/e2e/mysql extras, and pytest/ruff/mypy configuration with pinned critical packages. |
| `repo-scan.md` | Auto-generated full-repo dump produced by scan.sh, containing file tree and concatenated content of all tracked files for pasting to an external agent. |
| `scan.sh` | Bash script that collects git-tracked file paths and their text contents into a single markdown dump file (default repo-scan.md) for sharing with online agents. |

### app/

| File | Description |
|------|-------------|
| `__init__.py` | Package marker that declares the backend package version as 0.1.0. |
| `agent.py` | Implements the LLM dispatch loop supporting both Anthropic and PWR (OpenAI-compatible) backends with forced tool use, routing every query through catalog tools or respond_to_user before returning a structured reply. |
| `config.py` | Pydantic-settings configuration that loads API keys, model names, temperature, category_id_enum toggle, and LLM backend selector (PWR default, Anthropic fallback) from the .env file. |
| `main.py` | FastAPI application that exposes /api/chat, serves the widget static file, and maps both openai and anthropic RateLimitError exceptions to HTTP 429 responses. |
| `tools.py` | Single source of truth for all tool definitions (category_overview, search_products, respond_to_user) in Anthropic shape with auto-derived OpenAI shape, plus the dispatch function and stub handlers backed by data/categories_new.json. |

### data/

| File | Description |
|------|-------------|
| `categories_new.json` | 229 KB JSON array of webshop product categories, each with id, name, SEO fields (h1_title, meta_title, meta_description, og_title), intro text, cover image and icon — used as the category catalogue for the BitLab webshop. |
| `products.index.npz` | 7.1 MB NumPy compressed archive holding the vector index (384-dim embeddings from sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) for semantic product search over ~5,278 products. |
| `products.meta.json` | 6.1 MB JSON map of 5,278 product records (id, sifra, name, price, stock, category, brand, EAN, cover URL, search_text) aligned with the .npz index and used for retrieval metadata. |

### docs/

| File | Description |
|------|-------------|
| `PROMPT-BEST-PRACTICES.md` | Istraživanje standarda za e-commerce system prompt sa tool callingom, dijagnoza 29/29 apstinencija i preporuka za arhitekturni fix (tool_choice + respond_to_user + revive bck prompta). |
| `eval-infra-changelog.md` | Hronološki dnevnik dorada eval frameworka kroz Sesije 1 i 2: verdict cache, stratified sampler, budget tracker, cooperative PAUSE mehanizam i after-action kritika propusta. |
| `eval-infra-review.md` | Punch-list akcionabilnih popravki nakon Sesije 2 eval infrastrukture, sa statusom adresiranja svake tačke (kritični #1-4 i #9 adresirani, polish 5-11 ostali otvoreni). |
| `fb-funnel-progress.md` | Navigacioni dnevnik B2B akvizicijskog eksperimenta (FB funnel) sa statusom sibling repoa, timeline-om i trenutnim blokerom (FB skill-ovi odgođeni, pivot na LinkedIn). |
| `plans/akcioni-plan.md` | Strateški Now/Next/Later plan: Now inicijativa je fix eval regresije kategorija do acceptance ≥95% arhitekturnim forsiranjem tool callinga, Next su Faza 2 (RAG) i Faza 3 (multi-tool). |
| `work/2026-05-29-eval-acceptance/board.html` | Živi board za Now inicijativu evfx koji prikazuje odluke, orijentaciju i sljedeći korak (run_acceptance.sh batch runner do 250 case-ova), s rezultatom punog testa od 94%. |
| `work/2026-05-29-eval-acceptance/nalaz-fail-set-enum-temp.md` | Nalaz fail-set runa (enum+temperatura): 8/15 leaf-kolizija prošlo, preostalih 7 otpada na pogrešne-ali-validne leaf ID-eve, dvosmislene upite i typo known-limite, ne na leaf/parent selekciju. |

### evals/framework/

| File | Description |
|------|-------------|
| `__init__.py` (evals) | Empty marker file for the evals package. |
| `__init__.py` (evals/framework) | Package docstring describing the eval framework: one runner, unified schema via types.py, and a parser-based judge without LLM. |
| `budget.py` | Sliding 5-hour window PWR call tracker that signals the runner to pause (exit code 3) when calls reach 65% of the configurable MAX_CALLS=80 cap. |
| `cache.py` | Disk-backed SHA-256 verdict cache keyed on (entry + system_prompt + tools_signature) that avoids repeat PWR calls for deterministic inputs. |
| `client.py` | HTTP client that POSTs to /api/chat and raises RateLimitDetected on HTTP 429 so the runner can checkpoint instead of recording a generic FAIL. |
| `errors.py` | Defines RateLimitDetected, the single custom exception used to signal a backend rate-limit hit and trigger a runner checkpoint with exit code 3. |
| `judge.py` | Pure, deterministic, parser-based judge with three verdict layers (routing, result, overall) that requires no LLM calls to evaluate tool-call correctness. |
| `loader.py` | JSONL loader for eval suites that parses one entry per line, skips comments and blanks, validates required fields, and defaults optional ones. |
| `reporter.py` | Writes per-entry verdicts to a stable (non-timestamped) JSONL append log, generates an HTML dashboard, and prints a terminal summary for CI and ralph.sh. |
| `runner.py` | Main eval orchestrator that wires together loader, sampler, cache, budget, client, judge, and reporter with full resume/checkpoint support and exit codes 0–4. |
| `sampler.py` | Stratified sampler that reduces a 250-entry suite to ~30 reproducible entries by always including manual/negative cases and balancing parent vs leaf auto-gen entries. |
| `types.py` | TypedDict definitions for EvalEntry, ToolCall, HistoryMessage, ExpectClause, and EvalVerdict — the shared schema contract for the entire eval framework. |

### evals/sets/

| File | Description |
|------|-------------|
| `categories.jsonl` | Auto-generated master eval set for category routing, sourced from data/categories_new.json (SSOT); regenerated via scripts/gen_categories_eval.py. |
| `categories_acpt_fails.jsonl` | Hard acceptance-fail set of 15 overall-FAIL cases from the full acceptance run plus 8 negative examples, auto-generated by scripts/gen_acpt_fails.py. |
| `categories_dev.jsonl` | Hard dev sample of 29 regressions (cases that passed in iter8 but failed in iter17) plus 8 negative examples, auto-generated by scripts/gen_dev_sample.py. |
| `categories_leaf_tune.jsonl` | Manually curated tune set targeting leaf-routing failures and hallucinations from the 94.0% acceptance run — 15 routing FAILs and 6 false-positive hallucination cases. |
| `categories_manual.jsonl` | Hand-maintained negative-path eval set (never auto-generated) covering 4 subtypes — not_in_catalog, ambiguous_name, typo_likely, out_of_scope — where the model must not call any tool. |

### public/

| File | Description |
|------|-------------|
| `voice.html` | Standalone stranica za voice-only asistenta — animirani orb, VAD petlja (RMS threshold + onset/silence timer), STT/chat/TTS pipeline, sa render-erom za product card-ove i markdown u transcript sekciji. |
| `widget.html` | Demo webshop stranica (BitLab računari i elektronika) koja služi kao host za widget.js integraciju — sadrži nav, hero, trust bar, grid sa 4 proizvoda i footer. |
| `widget.js` | Embeddable chat widget v3 — injektuje se jednim script tagom, renderuje launcher dugme, chat prozor i voice overlay modal, sa VAD glasovnim modom, markdown+product card renderom, session ID trackiranjem i VOICE_ENABLED feature flag-om (trenutno false). |
| `assets/PITCH-BRIEF.md` | Kompletan brief za dizajnera pitch decka — brand boje, differentiator tabela, live demo flow skript, ROI kalkulacija i upute za 12 must-have slajdova za BitLab angažman prezentaciju. |
| `assets/favicon.ico` | Favicon ikona sajta u ICO formatu. |
| `assets/img/bitlabLogo.png` | BitLab logo u PNG formatu za upotrebu u UI-u i marketinškim materijalima. |
| `assets/BitLab AI Asistent — Engineering Pitch v2.pdf` | Engineering pitch prezentacija v2 u PDF formatu — finalna verzija pitch decka za BitLab klijenta. |
| `assets/BitLab AI Asistent.pdf` | Originalna ili alternativna verzija BitLab AI Asistent pitch prezentacije u PDF formatu. |
| `assets/BitLab_AI_Asistent.pptx` | Editabilna PowerPoint verzija pitch prezentacije za dalju iteraciju i prilagodbu. |

### ralph/

| File | Description |
|------|-------------|
| `AGENTS.md` | Operativni vodič za Ralph agenta — repo konvencije, komande, backpressure, git workflow i LLM backend dispatch pravila za svaku iteraciju. |
| `IMPLEMENTATION_PLAN.md` | Živi kanban koji Ralph čita i ažurira — Now/Next/Later/Done taskovi za Fazu 1 (kategorije eval) sa detaljnim per-iter PASS/FAIL breakdown-ima u Done sekciji. |
| `PROMPT_build.md` | Jedini prompt koji ralph.sh šalje Claude-u u build modu — vodi agenta kroz sedam faza od orient/pick-task do commit, eval, plan-update i STATUS ispisa. |
| `PROMPT_plan.md` | Prompt za plan mod (ralph-plan.sh) — instrukcije za gap analizu specs vs kod vs eval i restrukturiranje IMPLEMENTATION_PLAN.md bez ikakve implementacije. |
| `estimate_reset.py` | Helper koji procjenjuje kada se PWR 5h sliding window resetuje čitanjem najstarijeg `ts` iz pwr_calls.jsonl, vraća epoch za PAUSE marker. |
| `ralph-plan.sh` | Jednolinijska omotačica koja pokreće ralph.sh u plan modu s MAX_ITERS=1 i PROMPT_plan.md. |
| `ralph.sh` | Glavni orchestration loop — iterativno poziva `claude --print` s PROMPT_build.md, detektuje STOP/PAUSE markere, loguje u ralph/logs/ i postavlja fallback PAUSE kad eval runner exit-uje s kodom 3. |
| `status.sh` | Dashboard skripta koja prikazuje Ralph proces, PAUSE marker stanje, zadnjih 8 redova loga, posljednja 3 commita, Now/Done count iz IMPLEMENTATION_PLAN.md i PASS rate iz najnovijeg eval JSONL-a. |
| `wait_pause.py` | Python helper koji ralph.sh poziva kad postoji PAUSE marker — čeka (poll 300s) dok `until=<epoch>` ne istekne ili dok ne nestane fajl, vraća exit 1 ako se pojavi STOP marker. |
| `logs/iter29-rezum.log` | Eval runner output za iter29 rezum run — cache HIT redovi za cat-leaf-294, cat-leaf-299 i cat-leaf-311, sve PASS. |
| `logs/ralph-20260525-071044.log` | Ralph sesija pokrenuta 25.05.2026 u 07:10 — build mod, iter 1 od 100, sadržaj iteracije nije vidljiv u prvih 5 redova. |
| `logs/ralph-20260525-075845.log` | Ralph sesija pokrenuta 25.05.2026 u 07:58 — dokumentuje iter11 koja je pomaknula eval od 104 na 156 verdicata s 82.7% PASS ratom. |
| `logs/ralph-20260525-183906.log` | Ralph sesija pokrenuta 25.05.2026 u 18:39 u plan modu (MAX_ITERS=1) — jedan prolaz gap analize i push IMPLEMENTATION_PLAN.md ažuriranja (commit 40e330b). |

### scripts/

| File | Description |
|------|-------------|
| `__init__.py` | Package marker that identifies this directory as a collection of helper scripts for auto-generating eval sets and embed pipelines, not a runtime app dependency. |
| `gen_acpt_fails.py` | Generates a hard eval subset (categories_acpt_fails.jsonl) by extracting FAIL entries from the last full acceptance run and adding negative control cases, as a cheap gate before re-running the full 250-case suite. |
| `gen_categories_eval.py` | Auto-generates the canonical categories eval set (categories.jsonl) from data/categories_new.json by producing deterministic JSONL entries for leaf and parent categories following the rules in specs/categories.md. |
| `gen_dev_sample.py` | Generates a small hard dev eval subset (categories_dev.jsonl) by selecting regression cases (iter8 PASS → iter17 FAIL) plus negative controls, for fast/cheap prompt tuning without running the full suite. |
| `run_acceptance.sh` | Unattended batch runner that executes the full 250-case categories acceptance suite in batches of ~80, sleeping 5 hours between batches to wait for PWR session resets, resuming from where it left off. |
| `smoke.py` | Manual smoke script that runs the agent on a small set of representative queries and prints which tool was called and what reply was returned, for quick visual sanity-checking during prompt tuning without PASS/FAIL scoring. |

### specs/

| File | Description |
|------|-------------|
| `categories.md` | Definira pravila za rutiranje korisničkih upita u category_overview ili search_products alate, uključujući auto-generisanje eval setova, tool sheme i acceptance kriterije za Fazu 1 (PASS rate ≥ 95%). |
| `cross-reference.md` | Placeholder spec za Fazu 3 koji opisuje multi-tool kombinacije (kategorija x cijena x brand) u jednom upitu i pravila prioriteta argumenata, s acceptance kriterijem PASS rate ≥ 85%. |
| `products.md` | Placeholder spec za Fazu 2 koja pokriva RAG-baziranu pretragu proizvoda kroz search_products alat uz acceptance kriterij PASS rate ≥ 90%. |

### tests/

| File | Description |
|------|-------------|
| `conftest.py` | Defines shared pytest fixtures that mock both LLM clients (Anthropic and PWR) to prevent any real HTTP calls in the test suite. |
| `e2e/test_smoke.py` | Verifies that the Playwright library is importable in the e2e environment (skipped unless the e2e marker is explicitly invoked). |
| `integration/test_eval_runner_budget.py` | Tests that the eval runner checks the PWR budget before each entry, pauses with exit code 3 when the budget threshold is exhausted, records a call after each successful entry, and skips recording on cache hits. |
| `integration/test_eval_runner_cache.py` | Tests the eval runner end-to-end: output file creation, limit/dry-run behaviour, cache hit/miss/invalidation on signature change, sample-mode stratified selection, and fail-fast stopping. |
| `integration/test_eval_runner_resume.py` | Tests the runner's checkpoint-and-resume mechanism: writing a checkpoint and exiting with code 3 on rate limit, resuming from the saved index, appending to an existing stable JSONL, auto-detecting start index from verdicts, mode-mismatch abort (exit 4), and preserving the checkpoint on an empty resume range. |
| `integration/test_main_rate_limit.py` | Tests that the FastAPI app returns HTTP 429 (not 500) for both openai.RateLimitError and anthropic.RateLimitError, while leaving other errors as 500. |
| `integration/test_runner_writes_pause_marker.py` | Tests that the runner writes a PAUSE marker file with a valid future `until=<epoch>` on both budget-exhausted and rate-limit exits, and does not write it on clean completion; also verifies the reset-epoch estimation logic. |
| `integration/test_smoke.py` | Smoke tests for the FastAPI app via TestClient: healthz endpoint, PWR vs Anthropic backend routing, and empty-message validation rejection. |
| `integration/test_status_script.py` | Tests that ralph/status.sh exits zero, outputs all required dashboard sections, correctly reports when Ralph is not running, and shows the top Now task from IMPLEMENTATION_PLAN.md. |
| `integration/test_tool_dispatch.py` | Tests that category_overview and search_products tools are correctly dispatched through both the PWR and Anthropic backends and that the tool handler stubs return expected payloads. |
| `regression/test_smoke.py` | Placeholder regression-layer sanity test that confirms pytest collects the regression marker correctly. |
| `unit/test_eval_budget.py` | Unit tests for the sliding-window PWR call counter: record_call persistence, count_calls_last_5h filtering, and should_pause threshold logic. |
| `unit/test_eval_cache.py` | Unit tests for the eval verdict cache (compute_hash determinism, get/put roundtrip, NA skip, stats) and the stratified sampler (manual priority, parent/leaf balance, dedup, edge cases). |
| `unit/test_eval_client.py` | Unit tests for the eval HTTP client: HTTP 429 is mapped to RateLimitDetected, other status errors remain httpx.HTTPStatusError, and 2xx responses are returned as parsed JSON. |
| `unit/test_eval_errors.py` | Unit tests verifying that RateLimitDetected is a proper Exception subclass that preserves its message. |
| `unit/test_eval_framework.py` | Unit tests for the eval framework's pure functions: judge routing/result/overall verdict logic, JSONL suite loader validation, and HTML/JSONL reporter output. |
| `unit/test_gen_categories_eval.py` | Unit tests for the categories eval generator script: routing rules (leaf vs parent with ≥2 children), EvalEntry schema compliance, sort order, byte-identical determinism, and loader compatibility. |
| `unit/test_ralph_pause.py` | Unit tests for ralph/wait_pause.py (PAUSE marker parsing and poll loop) and ralph/estimate_reset.py (PWR reset epoch estimation from the call log). |
| `unit/test_ralph_prompt.py` | Unit tests that verify ralph/PROMPT_build.md and ralph/AGENTS.md contain required guardrail sections (STATUS block format, PWR-first rule, no-new-branch rule, sample-first rule, status.sh reference). |
| `unit/test_smoke.py` | Sanity unit smoke test: basic arithmetic and verification that the app package and its key attributes (run_agent, both backend runners, settings) are importable. |
| `unit/test_system_prompt.py` | Unit tests that SYSTEM_PROMPT_V1 is non-empty, references both tools, and is correctly passed as the system parameter to both the Anthropic and PWR runners. |

### var/

| File | Description |
|------|-------------|
| `bitlab.db` | SQLite database (1.7 MB) serving as the persistent data store for the application, likely holding conversation history and session state. |

### bck/

| File | Description |
|------|-------------|
| `bck/ (entire folder)` | 254-file archive of the full pre-reset bitLab AI asistent codebase, spanning application code, React dashboard, data assets, deployment configs, documentation, evaluation runs, n8n workflow definitions, utility scripts, and test suites. |
