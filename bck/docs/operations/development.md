# Razvojni workflow

## Grane

| Grana | Status | Šta sadrži |
|---|---|---|
| `main` | stabilno | MVP do Sesije 7 (chat + voice + email + n8n + security review) |
| `production-prep` | u review | Sesija 8: kategorije + dashboard + voice UX + hotfixovi (PR otvoren) |

Sesijski planovi: [`plans/`](./plans/).

## Workflow

1. Branch sa `main`, ime u formatu `<sesija>-<short-name>` (npr. `9-multi-provider-eval`)
2. Plan dokument na vrhu repo-a sa: model preporuka, DoD, stop-loss
3. Eval set ako diraš retrieval ili klasifikaciju (`evals/`)
4. Pytest mora biti zelen prije PR-a (i `not anthropic_api` markirovani lokalno)
5. PR opis ima Test plan sekciju i listu DoD ✅
6. Merge na `main` posle review-a + uspješnog server-side smoke testa

## Testovi

```bash
# Unit + integration (bez skupih API testova)
python -m pytest tests/ -m "not anthropic_api" -q

# Sa API testovima (skupo, ~$0.50 per run)
python -m pytest tests/ -q

# Samo specifičan regression set
python -m pytest tests/test_typo_robustness.py -v
python -m pytest tests/test_voice_tag_sanitization.py -v
python -m pytest tests/test_tts_normalization.py -v
python -m pytest tests/test_image_url_filter.py -v
python -m pytest tests/test_custom_build_response.py -v

# Eval — kategorija klasifikacija (target ≥80%)
python evals/run_categories.py

# Eval — format kompletan (Claude raw output)
python evals/run_format.py

# Smoke chat end-to-end (server mora raditi)
python scripts/smoke_test.py

# Dashboard build check (TS + Vite)
cd dashboard && pnpm build

# Deploy script syntax
bash -n scripts/deploy.sh

# Widget JS syntax
node -c public/widget.js

# Node renderer testovi
node --test tests/test_widget_renderer.mjs
```

## Modeli — kad koristiti šta

| Zadatak | Model | Razlog |
|---|---|---|
| Arhitekturne odluke (schema, abstraction layers) | **Opus 4.7 high** | Skupo se ispravlja kasnije |
| Port iz drugog repo-a (poznat materijal) | **Opus 4.7 high** | Jedan precizan pass < više iteracija |
| Polish, deploy, smoke, dokumentacija | **Sonnet 4.6 medium** | Obim posla, manje tokena |
| Trivijalne izmjene (typo, bump verzije) | **Sonnet 4.6 low** | — |

## Test markeri

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = [
    "anthropic_api: integration tests koji zovu pravi Anthropic API (skup, ~$0.02 po test)",
]
```

CI config (kad budemo dodali GitHub Actions):
- PR pre-merge: `pytest -m "not anthropic_api"` — brzo, ~70s
- Mjesečno + manualno: `pytest` (sa anthropic_api) — sigurnost da prompt nije regredirao

## File patterns

```
app/                        Backend Python
├── main.py                 FastAPI entry, endpointi
├── agent.py                Claude tool-use loop
├── tools.py                Tool schemas + handlers
├── rag.py                  Hibrid search
├── faq.py                  FAQ retrieval
├── system_prompts.py       Prompt template-i (chat/voice/email)
├── server/                 Dashboard API
└── storage/                SQLAlchemy modeli + repo

dashboard/src/              React 19 + Vite 8 + TS
├── pages/                  6 stranica (Live, History, Compare, RequestDetail, Stats, Settings)
├── components/             Layout + atoms
├── api.ts                  axios client + Bearer interceptor
└── tokens.ts               dark theme + per-channel/model boje

evals/                      Eval scripts + JSON datasets
tests/                      pytest + Node renderer tests
scripts/                    Build, deploy, audit helpers
deploy/                     systemd unit + nginx config šabloni
public/                     widget.js, widget.html, voice.html
data/                       JSON + npz (categories, meta, faq, missing_images)
docs/                       Ova dokumentacija
```

## Linting / formatiranje

`pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py311"
```

Ručno: `ruff check app/ tests/ evals/ scripts/`

Dashboard: `pnpm lint` (eslint + typescript-eslint).

## Pre-commit hook (opciono)

Trenutno nema. Predlog za dodavanje:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.0
    hooks: [{id: ruff}]
  - repo: local
    hooks:
      - id: pytest-fast
        name: pytest fast
        entry: python -m pytest tests/ -m "not anthropic_api" -q
        language: system
        pass_filenames: false
```

## Modelska iteracija

Kad mijenjaš system prompt:
1. Edituj `app/system_prompts.py`
2. Pokreni eval: `python evals/run_categories.py` + `python evals/run_format.py`
3. Ako pass rate padne, ne mergaj — vraćaj ili dodaj test case
4. Compare panel u dashboard-u (`/admin/compare`) — testiraj specifične upite kroz oba modela
5. Ako dodaješ novo pravilo, dodaj eval scenario u relevantni JSON

## Adding a new tool

1. Tool schema u `tools.py` (Anthropic format: `{name, description, input_schema}`)
2. Handler funkcija (`handle_xxx(...)`)
3. Dodaj u `_HANDLERS` dict + `ALL_TOOLS` lista
4. Update system prompt (`BITLAB_BASE`) sa kratkim opisom kad ga koristiti
5. Tracker auto-loguje (kroz `dispatch()` wrapper u `agent.py`)

## Adding a new dashboard page

1. `dashboard/src/pages/X.tsx` — koristi `Layout` automatski
2. Dodaj rutu u `dashboard/src/App.tsx`
3. Dodaj nav link u `dashboard/src/components/Layout.tsx` `NAV` array
4. Backend endpoint (ako treba) u `app/server/dashboard.py` pod `/api/dashboard/...`
5. API client method u `dashboard/src/api.ts`
6. `pnpm build` mora proći bez TS greška

## Dependency management

Python: `pyproject.toml` `[project.dependencies]` lista. Pin only major (`>=`).

Node: `dashboard/package.json` + `pnpm-lock.yaml`. Frozen-lockfile u CI.

Dodavanje nove deps:
- Python: `pip install x` lokalno → testiraj → dopuni `pyproject.toml` ručno → commit `pyproject.toml`
- Node: `cd dashboard && pnpm add x` → automatski update `package.json` + lockfile → commit oba

## Test coverage trenutno

| Kategorija | Pokrivenost |
|---|---|
| Tool dispatch | unit testovi za sva 4 toola |
| RAG search | smoke testovi + image_url filter |
| TTS normalizacija | 11 testova (cijene, jedinice) |
| Voice/chat tag sanitization | 16 testova |
| Multi-line product collapse | 10 Node testova |
| Custom build response | 4 anthropic_api testova |
| Typo robustnost | 6 anthropic_api testova |
| Image URL filter | 5 testova |
| Category eval | 41 upit, 100% baseline |
| Format eval | 5 upita raw Claude output |

Total: **62 unit/integration + 41 category eval + 10 Node**.

## Profiling / performance

Trenutno nema benchmark suite. Ako treba:
- p50/p95 latency: `Stats` tab dashboarda po request-u
- API cost: ista tabela
- Embedding speed: `cProfile` na `idx.search()` direktno

Predlog za Sesiju 11+: dodati `evals/run_perf.py` koji mjeri 100 paralelnih chat upita i izvještava p50/p95.
