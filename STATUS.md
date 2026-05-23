# STATUS — bitlab-ai-asistent

Strateški Kanban (vodič za čovjeka). Taktički/dnevni rad u `ralph/IMPLEMENTATION_PLAN.md` (ne dupliciraj entry-je ovdje).

## Now

- **Faza 1: TDD eval framework za kategorije** (Ralph driven). Acceptance: `python -m evals.framework.runner --suite categories` PASS rate ≥ 95%. Detaljni taskovi u `ralph/IMPLEMENTATION_PLAN.md` Now sekciji.

## Next

- **Faza 2: Eval za proizvode** (RAG `search_products`). Spec: `specs/products.md`. Cherry-pick iz `bck/app/rag.py`.
- **Faza 3: Cross-reference** (multi-tool sekvence). Spec: `specs/cross-reference.md`.
- **bitlab-standards full adopcija**: bootstrap-status / decompose-initiative skill-ovi rade na ovom repou.

## Later

- Voice modul (faster-whisper) povratak iz `bck/`.
- Email auto-reply iz `bck/`.
- Dashboard frontend (`dashboard/`) povratak.
- N8N integracije (vidi memoriju `project_n8n_setup_state`).

## Done

- 2026-05-24 **Faza 0**: Ralph petlja + TDD eval framework infrastruktura. Test piramide (`tests/{unit,integration,e2e,regression}/`) sa mock_anthropic. CI/e2e/eval-nightly workflows. Pre-commit hooks. `ralph/` state files (AGENTS.md, PROMPT_build.md, PROMPT_plan.md, IMPLEMENTATION_PLAN.md, ralph.sh, ralph-plan.sh). `evals/framework/` runner sa parser-based judge. STATUS.md (ovaj fajl). Commit: `feat(ralph): infra — petlja, prompts, test pyramide, eval framework skeleton`.
