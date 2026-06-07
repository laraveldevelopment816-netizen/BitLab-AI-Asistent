# Repo Inventory — bitlab-ai-asistent

Status-classified file inventory grouped by logical component.

- **Generated:** 2026-06-07 · branch `feat/ralph-categories-eval`
- **Scope:** all 360 git-tracked files. The 254 files under `bck/` are summarized as a single row (the archive exception); the other 106 files are classified individually.
- **Method:** 13 Sonnet scan agents read & classified files by component (each grepped the repo to confirm references before any DEAD call), then the results were verified and synthesized. Where verification overturned a raw scan verdict, the corrected status is used and the reason is noted at the bottom.
- **Context:** this repo is mid a *TDD zero-base reset* — all of the old full-stack code was deliberately moved into `bck/` and a minimal core is being rebuilt, driven by failing eval entries. The current Now initiative is fixing the categories-routing eval regression (iter17 dropped 84.4% → 79.2%) back up to ≥95% acceptance by forcing tool calls.

## Legend

- **ACTIVE** — part of the current working system: imported/run by the live app, the eval framework, current tests, the Ralph loop, current scripts/config/CI, or planning docs that reflect present work.
- **DRAFT** — work-in-progress or placeholder for not-yet-built work (e.g. future-phase specs).
- **ARCHIVED** — deliberately kept for reference but not part of the active system (the `bck/` tree, retained run artifacts, intentional collateral).
- **DEAD** — orphaned, superseded, or safe to delete; not referenced by anything active.

## Summary

| Status | Count |
|---|---|
| ACTIVE | 96 |
| ARCHIVED | 8 |
| DRAFT | 2 |
| DEAD | 1 |
| **Total** | **107** (106 files + `bck/` as one row) |

The active codebase is healthy and tightly scoped: nearly everything tracked is load-bearing for the current categories-eval work. There is exactly one removable file (`evals/sets/.gitkeep`), two DRAFT specs for future phases, and a handful of intentionally-retained reference/collateral files.

---

## 1. Backend application — `app/`, `data/`

The deployable core after the reset: a minimal FastAPI service whose only real endpoint, `/api/chat`, runs a forced-tool-use dispatch loop over two interchangeable LLM backends (PWR by default, Anthropic as fallback) and routes every query through catalog tools defined once in `tools.py`. `config.py` centralizes settings (model, temperature, the `category_id` enum toggle, backend selector) and `data/categories_new.json` is the live taxonomy that backs the tool stubs and every eval. All six files are ACTIVE and load-bearing — this is the surface the current routing initiative is tuning.

| File | Status | What it does |
|---|---|---|
| `app/__init__.py` | ACTIVE | Marks the `app` directory as a Python package and exposes the version string; imported transitively by the eval runner, tests, and scripts. |
| `app/agent.py` | ACTIVE | Implements `run_agent`, the forced-tool-use LLM dispatch loop (Anthropic + PWR backends) called by `main.py` on every `/api/chat` request and exercised by the eval framework. |
| `app/config.py` | ACTIVE | Defines the `Settings` pydantic model (API keys, model, temperature, `category_id_enum` flag, backend selector) imported by `agent.py` and `tools.py` at startup. |
| `app/main.py` | ACTIVE | The live FastAPI entry point: mounts `/public` static files, registers openai+anthropic rate-limit→429 handlers, and exposes `/`, `/healthz`, and `/api/chat`. |
| `app/tools.py` | ACTIVE | Single source of truth for the tool schemas (`category_overview`, `search_products`, `respond_to_user`) in both Anthropic and OpenAI shapes, plus the `dispatch` handler backed by `data/categories_new.json`. |
| `data/categories_new.json` | ACTIVE | The live category taxonomy loaded at startup by `tools.py` to build parent/leaf ID enums and child-category lookups used in every eval and integration test. |

## 2. Browser frontend — `public/`

The client side served straight off the FastAPI static mount: `widget.html` is the demo host page returned at `/`, `widget.js` is the embeddable v3 chat widget (with a voice overlay gated off via `VOICE_ENABLED=false`), and `voice.html` is the standalone voice page the widget links to as a fallback. `favicon.ico` is in active use; the remaining assets — the pitch brief, the two pitch PDFs, the PPTX, and `bitlabLogo.png` — are deliberately-kept marketing collateral with no code references, classified ARCHIVED rather than deleted.

| File | Status | What it does |
|---|---|---|
| `public/widget.html` | ACTIVE | Demo webshop host page served by `main.py` at `/`, embedding `widget.js` as the live chat interface. |
| `public/widget.js` | ACTIVE | Embeddable chat widget v3 (markdown + product cards, session tracking, voice overlay) loaded via script tag in `widget.html`; in-widget voice overlay is gated off by `VOICE_ENABLED=false`. |
| `public/voice.html` | ACTIVE | Standalone voice-only assistant page (animated orb, VAD loop, STT/chat/TTS) served at `/public/voice.html` and linked from `widget.js` as the voice fallback — the current voice entry point while the embedded overlay stays disabled. |
| `public/assets/favicon.ico` | ACTIVE | Browser tab icon referenced by both `widget.html` and `voice.html` and served via the static mount. |
| `public/assets/PITCH-BRIEF.md` | ARCHIVED | Complete designer brief for the pitch deck (brand, differentiators, demo flow, ROI, 12-slide spec); deliberately kept marketing collateral with no code references. |
| `public/assets/img/bitlabLogo.png` | ARCHIVED | BitLab brand logo kept as collateral; not referenced by any served HTML/JS (`favicon.ico` is the asset actually in use). |
| `public/assets/BitLab AI Asistent — Engineering Pitch v2.pdf` | ARCHIVED | Engineering pitch deck PDF retained as marketing collateral, unreferenced by any running code. |
| `public/assets/BitLab AI Asistent.pdf` | ARCHIVED | Original pitch deck PDF retained as marketing collateral, unreferenced by any running code. |
| `public/assets/BitLab_AI_Asistent.pptx` | ARCHIVED | Editable PowerPoint pitch deck retained as marketing collateral, unreferenced by any running code. |

## 3. Eval framework — `evals/framework/`

The deterministic, parser-based evaluation engine that is the backbone of the whole TDD approach: one `runner.py` wires together the JSONL `loader`, stratified `sampler`, SHA-256 verdict `cache`, sliding-window PWR `budget` tracker, HTTP `client`, pure `judge`, and HTML/JSONL `reporter`, all typed against one shared `types.py` contract. Every file is ACTIVE; the framework supports checkpoint/resume and rate-limit-safe pausing so long 250-case runs survive PWR session resets.

| File | Status | What it does |
|---|---|---|
| `evals/__init__.py` | ACTIVE | Package init for the `evals` namespace. |
| `evals/framework/__init__.py` | ACTIVE | Package init documenting the framework's unified schema and runner invocation. |
| `evals/framework/budget.py` | ACTIVE | Tracks PWR API calls in a sliding 5-hour window and signals the runner to pause before exhausting the budget. |
| `evals/framework/cache.py` | ACTIVE | Disk-backed SHA-256 verdict cache that skips repeat PWR calls when prompt and tools are unchanged. |
| `evals/framework/client.py` | ACTIVE | HTTP client that POSTs eval queries to `/api/chat` and raises `RateLimitDetected` on HTTP 429. |
| `evals/framework/errors.py` | ACTIVE | Defines `RateLimitDetected`, the custom exception propagated from client to runner for checkpoint-safe handling. |
| `evals/framework/judge.py` | ACTIVE | Pure deterministic judge producing routing/result/overall verdicts from eval entries and actual tool calls. |
| `evals/framework/loader.py` | ACTIVE | Loads and validates JSONL eval suites, enforcing required fields and defaulting optional ones. |
| `evals/framework/reporter.py` | ACTIVE | Writes per-entry JSONL append logs, timestamped HTML dashboards, and terminal summaries for each run. |
| `evals/framework/runner.py` | ACTIVE | Orchestrates full suite execution with cache, budget gating, checkpoint/resume, and sampling modes. |
| `evals/framework/sampler.py` | ACTIVE | Produces a reproducible stratified ~30-entry sample to cut PWR cost per Ralph iteration. |
| `evals/framework/types.py` | ACTIVE | Defines the canonical TypedDicts (EvalEntry, EvalVerdict, ToolCall, ExpectClause) shared across the framework. |

## 4. Eval data sets & run artifacts — `evals/sets/`, `evals/runs/`

The corpora the framework runs against: a canonical auto-generated `categories.jsonl` master suite plus four focused subsets (hard dev sample, acceptance-fail set, leaf-tune set, hand-maintained negatives) that implement the "develop on a hard sample, full eval once" discipline from `STATUS.md`. The stable `categories-acpt.jsonl` log is ACTIVE, the timestamped HTML report is a retained ARCHIVED artifact, and the leftover `.gitkeep` is now redundant since the directory is populated.

| File | Status | What it does |
|---|---|---|
| `evals/sets/categories.jsonl` | ACTIVE | Auto-generated primary eval suite (254 entries) loaded as the canonical "categories" suite for acceptance and regression runs. |
| `evals/sets/categories_acpt_fails.jsonl` | ACTIVE | Auto-generated hard sub-set (15 acceptance failures + 8 negatives) from the last full run, used as a cheap regression gate. |
| `evals/sets/categories_dev.jsonl` | ACTIVE | Auto-generated hard dev sample (29 iter8→iter17 regressions + 8 negatives) for fast/cheap prompt iteration. |
| `evals/sets/categories_leaf_tune.jsonl` | ACTIVE | Manually curated tune set (15 leaf-routing failures + 6 hallucination false-positives); the validation set for the current leaf-routing fix. |
| `evals/sets/categories_manual.jsonl` | ACTIVE | Hand-maintained negative set (`expect.tool=null`) feeding the dev/acpt generators with out-of-catalog and ambiguous cases. |
| `evals/sets/.gitkeep` | DEAD | Redundant directory placeholder — the folder now holds real eval sets, so it serves no purpose. |
| `evals/runs/categories-acpt.jsonl` | ACTIVE | Stable (non-timestamped) JSONL log appended by `run_acceptance.sh` and the runner as the canonical record of the 250-case acceptance results. |
| `evals/runs/categories-acpt-20260607-130937.html` | ARCHIVED | Timestamped HTML report for the latest full 250-case run (commit `075affc`); retained historical artifact, not referenced by any active script. |

## 5. Eval-set generators & smoke tooling — `scripts/`

The regenerable pipeline that produces those data sets from the source of truth: `gen_categories_eval.py` derives the canonical suite from `data/categories_new.json` per `specs/categories.md`, while `gen_acpt_fails.py` and `gen_dev_sample.py` carve the hard subsets out of prior run verdicts, `run_acceptance.sh` drives the batched 250-case acceptance gate, and `smoke.py` is the no-scoring eyeball tool for prompt tuning. All ACTIVE and tied directly to the current initiative.

| File | Status | What it does |
|---|---|---|
| `scripts/__init__.py` | ACTIVE | Makes `scripts/` a package so generators run as `python -m scripts.*` and import into the unit tests. |
| `scripts/gen_categories_eval.py` | ACTIVE | Auto-generates the canonical `categories.jsonl` from `data/categories_new.json` per `specs/categories.md`; unit-tested. |
| `scripts/gen_acpt_fails.py` | ACTIVE | Generates `categories_acpt_fails.jsonl` from the last acceptance run's FAIL verdicts plus negatives, as a cheap gate. |
| `scripts/gen_dev_sample.py` | ACTIVE | Generates the fast-feedback `categories_dev.jsonl` from iter8-PASS/iter17-FAIL regressions plus negatives. |
| `scripts/run_acceptance.sh` | ACTIVE | Runs the full 250-entry acceptance suite in batches that resume across PWR session resets; the acceptance gate named in `STATUS.md`. |
| `scripts/smoke.py` | ACTIVE | Manual no-scoring eyeball tool that calls `run_agent` on representative queries to inspect routing while tuning the prompt. |

## 6. Ralph autonomous TDD loop — `ralph/`

The self-driving harness that runs the build cycle unattended: `ralph.sh` feeds `PROMPT_build.md` to the Claude CLI each iteration, honoring STOP/PAUSE markers and calling `wait_pause.py`/`estimate_reset.py` to back off around PWR's 5-hour window, with `IMPLEMENTATION_PLAN.md` as the live task board, `AGENTS.md` as the operating manual, and `status.sh` as the dashboard. All ACTIVE — though the action plan flags an open question (`evfx`) about whether the autonomous loop is still needed now that tool-calling is forced mechanically.

| File | Status | What it does |
|---|---|---|
| `ralph/ralph.sh` | ACTIVE | Main autonomous TDD loop driver that feeds `PROMPT_build.md` to the Claude CLI, handles STOP/PAUSE markers, and calls the pause/reset helpers. |
| `ralph/ralph-plan.sh` | ACTIVE | One-liner wrapper that launches a single plan-mode iteration with `PROMPT_plan.md`. |
| `ralph/PROMPT_build.md` | ACTIVE | The build-mode prompt that drives Claude through orient → implement → backpressure → commit each iteration. |
| `ralph/PROMPT_plan.md` | ACTIVE | The plan-mode prompt instructing gap analysis and `IMPLEMENTATION_PLAN.md` updates without touching app code. |
| `ralph/AGENTS.md` | ACTIVE | Operating manual each iteration reads first: repo commands, backpressure rules, LLM dispatch imperatives, loop rules. |
| `ralph/IMPLEMENTATION_PLAN.md` | ACTIVE | Live Now/Next/Done board Ralph reads to pick the top task and updates after each iteration. |
| `ralph/status.sh` | ACTIVE | Dashboard reporting Ralph process state, last log lines, recent commits, plan task counts, and latest eval PASS rate. |
| `ralph/wait_pause.py` | ACTIVE | Helper that polls the PAUSE marker until the auto-resume epoch (or cooperative `rm`), signaling continue vs exit. |
| `ralph/estimate_reset.py` | ACTIVE | Helper invoked on exit code 3 to estimate the PWR rate-limit window reset epoch; unit- and integration-tested. |
| `ralph/logs/.gitkeep` | ACTIVE | Keeps the gitignored `ralph/logs/` directory present so `ralph.sh` can write timestamped logs there. |

## 7. Test suite — `tests/`

A full pytest pyramid (`unit`, `integration`, `e2e`, `regression`) with a `conftest.py` that mocks both LLM clients so no test ever hits a real API (a hard budget constraint). Coverage skews — appropriately — toward the eval framework and the Ralph helpers; every file is ACTIVE, with the e2e and regression layers currently thin placeholders that grow as eval entries start passing.

| File | Status | What it does |
|---|---|---|
| `tests/conftest.py` | ACTIVE | Shared fixtures (mock LLM clients, test client, backend forcing) that prevent real LLM calls across the whole suite. |
| `tests/__init__.py` | ACTIVE | Package marker enabling pytest discovery of the `tests/` package. |
| `tests/unit/__init__.py` | ACTIVE | Package marker enabling pytest discovery of the `unit` layer. |
| `tests/integration/__init__.py` | ACTIVE | Package marker enabling pytest discovery of the `integration` layer. |
| `tests/e2e/__init__.py` | ACTIVE | Package marker enabling pytest discovery of the `e2e` layer. |
| `tests/regression/__init__.py` | ACTIVE | Package marker enabling pytest discovery of the `regression` layer. |
| `tests/unit/test_eval_budget.py` | ACTIVE | Unit tests for the budget tracker's sliding-window counter and pause threshold. |
| `tests/unit/test_eval_cache.py` | ACTIVE | Unit tests for the verdict cache and the stratified sampler. |
| `tests/unit/test_eval_client.py` | ACTIVE | Unit tests that HTTP 429 → `RateLimitDetected` while other errors propagate. |
| `tests/unit/test_eval_errors.py` | ACTIVE | Unit tests that `RateLimitDetected` is a proper Exception preserving its message. |
| `tests/unit/test_eval_framework.py` | ACTIVE | Unit tests for the judge/loader/reporter pure functions. |
| `tests/unit/test_gen_categories_eval.py` | ACTIVE | Unit tests for the categories generator (routing rules, schema, deterministic output). |
| `tests/unit/test_ralph_pause.py` | ACTIVE | Unit tests for `wait_pause.py` and `estimate_reset.py`. |
| `tests/unit/test_ralph_prompt.py` | ACTIVE | Guard tests that the Ralph prompt/AGENTS files contain required guardrail sections. |
| `tests/unit/test_smoke.py` | ACTIVE | Confirms the `app` package and its dual-backend attributes are importable. |
| `tests/unit/test_system_prompt.py` | ACTIVE | Verifies `SYSTEM_PROMPT_V1` is defined, names both tools, and reaches both runners. |
| `tests/integration/test_eval_runner_budget.py` | ACTIVE | Integration tests of runner↔budget gating and the cache-hit-no-budget invariant. |
| `tests/integration/test_eval_runner_cache.py` | ACTIVE | Integration tests of runner cache hit/miss, limit, fail-fast, sample mode, and invalidation. |
| `tests/integration/test_eval_runner_resume.py` | ACTIVE | Integration tests of checkpoint/resume, mode-mismatch detection, and auto-detect start index. |
| `tests/integration/test_main_rate_limit.py` | ACTIVE | Integration tests that FastAPI maps both SDKs' `RateLimitError` to HTTP 429. |
| `tests/integration/test_runner_writes_pause_marker.py` | ACTIVE | Integration tests that a valid PAUSE marker is written on budget/rate-limit exits and omitted on clean completion. |
| `tests/integration/test_smoke.py` | ACTIVE | Integration smoke for `/healthz` and `/api/chat` with both backends mocked. |
| `tests/integration/test_status_script.py` | ACTIVE | Runs `ralph/status.sh` and asserts exit 0 plus all dashboard sections. |
| `tests/integration/test_tool_dispatch.py` | ACTIVE | Integration tests of tool dispatch through both backends and the handler return shapes. |
| `tests/e2e/test_smoke.py` | ACTIVE | E2e smoke that Playwright is importable, skipping when the browser toolchain is absent. |
| `tests/regression/test_smoke.py` | ACTIVE | Regression-layer placeholder seed that grows as eval entries pass. |

## 8. Specifications — `specs/`

The phase contracts: `categories.md` is the ACTIVE Faza 1 spec that drives tool schemas, eval generation, and acceptance criteria, while `products.md` (Faza 2 RAG) and `cross-reference.md` (Faza 3 multi-tool) are explicit DRAFT placeholders for unbuilt future phases.

| File | Status | What it does |
|---|---|---|
| `specs/categories.md` | ACTIVE | Faza 1 categories-routing spec (tool schemas, eval-generation rules, ≥95% acceptance) actively driving `tools.py`, tests, the generator, and Ralph. |
| `specs/products.md` | DRAFT | Placeholder Faza 2 spec for RAG product search, explicitly not-yet-implemented and pending Faza 1 acceptance. |
| `specs/cross-reference.md` | DRAFT | Placeholder Faza 3 spec for multi-tool cross-reference queries (category × price × brand), awaiting Faza 2. |

## 9. Documentation, planning & status — root `*.md`, `docs/`

The two-level planning model plus supporting analysis: `STATUS.md`/`STATUS-HUMAN.md` are the tactical Kanban (machine + human), `docs/plans/akcioni-plan.md` the strategic Now/Next/Later, `PLAN.md` the foundational TDD-reset rules, and `RESTORE.md` the recipe to rebuild the full app from `bck/`. Alongside are the post-mortems and infra logs (`EVAL_REGRESIJA_iter17.md`, `EVAL_OPTIMIZACIJA.md`, `docs/eval-infra-*`, `docs/PROMPT-BEST-PRACTICES.md`, the `docs/work/...` session board) that directly inform the current fix. Almost all ACTIVE; the two `repo-map*.md` catalogues are current maintained snapshots (regenerated today), and `docs/fb-funnel-progress.md` is an ARCHIVED pointer to an unrelated sibling-repo experiment.

| File | Status | What it does |
|---|---|---|
| `STATUS.md` | ACTIVE | Formal Kanban tracking the active Doing/Todo tasks for the categories routing fix, plus known limitations and eval discipline rules. |
| `STATUS-HUMAN.md` | ACTIVE | Plain-language companion to `STATUS.md` explaining the regression and each card for quick human orientation. |
| `PLAN.md` | ACTIVE | The TDD zero-base reset plan (foundational rules) that `STATUS.md` links to. |
| `README.md` | ACTIVE | Developer quick-start: Ralph commands, eval runner invocations, the chunked 250-case acceptance runner. |
| `RESTORE.md` | ACTIVE | Recipe to recover the full pre-reset app from `bck/`; the live safety net during the rebuild. |
| `EVAL_REGRESIJA_iter17.md` | ACTIVE | Post-mortem of the iter17 regression (84.4% → 79.2%) defining baseline, root cause, and the recovery roadmap driving the Now initiative. |
| `EVAL_OPTIMIZACIJA.md` | ACTIVE | Design doc of five PWR cost-reduction strategies plus the rate-limit-checkpoint code review now implemented in the eval infra. |
| `CLAUDE.md` | ACTIVE | Project Claude Code config: deployment URLs + import of shared bitlab-standards rules, loaded every session. |
| `repo-map.md` | ACTIVE | Maintained full-repo catalogue with per-file descriptions (regenerated 2026-06-07); current docs snapshot, complementary to this file. |
| `repo-map-simplified.md` | ACTIVE | Maintained status-tagged simplified catalogue; current human-readable docs snapshot. |
| `docs/plans/akcioni-plan.md` | ACTIVE | The strategic Now/Next/Later plan defining the Now initiative (categories eval to ≥95%) and scoping Faza 2/3. |
| `docs/PROMPT-BEST-PRACTICES.md` | ACTIVE | Research/recommendations on `tool_choice` + prompt architecture that inform the current fix; referenced in `STATUS.md`. |
| `docs/eval-infra-changelog.md` | ACTIVE | Chronological after-action log of eval-infra sessions (cache, sampler, resume, budget, PAUSE); referenced in `README.md`. |
| `docs/eval-infra-review.md` | ACTIVE | Punch-list review of Session 2 eval infra tracking which fixes landed and which polish items remain. |
| `docs/work/2026-05-29-eval-acceptance/board.html` | ACTIVE | Live session board for the Now initiative showing decisions, orientation, and next steps. |
| `docs/work/2026-05-29-eval-acceptance/nalaz-fail-set-enum-temp.md` | ACTIVE | 2026-06-05 analysis of the enum+temperature fail-set run identifying the 7 remaining failures and the next step. |
| `docs/fb-funnel-progress.md` | ARCHIVED | Navigation log for a separate B2B acquisition experiment in sibling repos (`ralph-fb-funnel`/`-prospector`); dormant and out of scope for this repo's categories-eval work. |

## 10. Build config & CI — `.github/`, root config

The toolchain and gates: `pyproject.toml` defines deps and ruff/mypy/pytest config, `.pre-commit-config.yaml` enforces them on every commit, `.gitattributes`/`.gitignore`/`.env.example` handle hygiene and secrets, `scan.sh` produces the external-agent repo dump, and three GitHub Actions workflows run CI (ruff/mypy/pytest), Playwright e2e, and a nightly real-LLM eval. All ACTIVE.

| File | Status | What it does |
|---|---|---|
| `pyproject.toml` | ACTIVE | Project deps, build config, and ruff/mypy/pytest settings and test markers for the whole system. |
| `.pre-commit-config.yaml` | ACTIVE | Pre-commit hooks (ruff format/lint, mypy, pytest unit) gating every commit. |
| `.gitignore` | ACTIVE | Excludes build artifacts, secrets, eval caches, Ralph markers, and generated data. |
| `.gitattributes` | ACTIVE | Enforces LF endings for text/shell files to avoid CRLF churn on WSL/Windows. |
| `.env.example` | ACTIVE | Template of all required/optional env vars (LLM backend, TTS/STT, webshop, eval overrides). |
| `scan.sh` | ACTIVE | Generates the single-file `repo-scan.md` dump of all tracked text files for external agents. |
| `.github/workflows/ci.yml` | ACTIVE | Runs ruff, mypy, and pytest (unit + integration) on push/PR to the tdd-zero-base and `feat/**` branches. |
| `.github/workflows/e2e.yml` | ACTIVE | Runs Playwright e2e tests on PRs to the integration branch. |
| `.github/workflows/eval-nightly.yml` | ACTIVE | Runs the real-LLM categories eval nightly at 03:00 UTC and uploads artifacts. |

## 11. Pre-reset archive — `bck/`

| Folder | Status | What it does |
|---|---|---|
| `bck/` | ARCHIVED | Pre-reset archive of the old full-stack codebase (254 tracked files) — app code, the React dashboard, data assets, deploy configs, docs, evals, n8n workflows, scripts, and tests — kept for reference and restorable via `RESTORE.md`, but not imported or run by any part of the active system. |

---

## Notes

**Untracked on-disk artifacts** (not among the 360 tracked files, so not classified above): `repo-scan.md` (~21 MB, generated by `scan.sh`), `var/bitlab.db` (~1.7 MB SQLite, gitignored), an untracked `dashboard/` directory, and tooling caches (`.venv`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.idea`, `bitlab_ai_asistent.egg-info`). All are regenerated or local and can be ignored for inventory purposes.

**Judgment calls** (where the raw scan was overridden after verifying references):
- `public/voice.html` → **ACTIVE** (not DEAD): linked from `widget.js:1899` and served by the `/public` static mount in `main.py`; deleting it would break the voice fallback.
- pitch deck / brief / logo (`PITCH-BRIEF.md`, both PDFs, the PPTX, `bitlabLogo.png`) → **ARCHIVED** (not DEAD): intentional marketing collateral, not orphaned leftovers.
- `repo-map.md`, `repo-map-simplified.md` → **ACTIVE** (not DRAFT): committed and regenerated 2026-06-07, i.e. maintained current documentation.
- `docs/fb-funnel-progress.md` → **ARCHIVED** (not DEAD): a cross-repo pointer to a dormant sibling-repo experiment, kept for reference.
- `evals/sets/.gitkeep` is the only genuinely removable file — the directory it was holding open is now populated.
