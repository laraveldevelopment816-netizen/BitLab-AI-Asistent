# Handoff: Conduit — AI Browser Router

> Local point-of-presence that exposes an OpenAI-compatible REST API and proxies prompts to logged-in browser sessions of Claude.ai, ChatGPT, DeepSeek, Grok (and Ollama as a native fallback) via Playwright.

---

## Overview

**Conduit** is a developer tool. You run it locally (or on a staging server). Your editor / CLI / scripts talk to it as if it were the OpenAI API. Under the hood it drives real browsers, signed in to AI provider websites, types in your prompt, and scrapes the response.

**Why this exists:**
- Use existing AI subscriptions instead of paying per-token API fees during development
- Single API surface for many providers — swap underlying provider without changing client code
- Track everything: every prompt, every response, token counts, latency, cost projection
- Migrate to real APIs later by swapping the adapter implementation — client code never changes

**Primary user:** the developer (you), running this locally and pointing tools like Cursor / Continue / `curl` / custom scripts at it.

---

## About the Design Files

The files under `prototype/` are **design references** built in HTML/React. They are **not** production code. They show:
- What the dashboard should look and feel like (colors, type, spacing, density, motion)
- The information architecture (tabs, drawers, cards, charts)
- The interaction patterns (live stream, filter+search, fan-out compare, replay, tweaks)

Your job is to **build the real Conduit** — a Python backend (FastAPI + Playwright + SQLite) plus a React+TypeScript dashboard — and **recreate the prototype's UI inside that new dashboard**. Treat the prototype as a Figma-equivalent: lift colors, copy, layout, micro-interactions; do not lift the inline-styled JSX literally.

---

## Fidelity

**High-fidelity.** Colors, typography, spacing, micro-interactions, copy — all final unless noted. Match the prototype pixel-for-pixel where reasonable.

---

## Tech stack (prescribed)

| Layer | Choice | Why |
|---|---|---|
| Backend language | **Python 3.12** | User preference; great Playwright bindings |
| Web framework | **FastAPI** | Async, auto OpenAPI, SSE-ready |
| Browser automation | **Playwright (async)** + `playwright-stealth` | Cloudflare-resilient |
| ORM | **SQLModel** (Pydantic + SQLAlchemy) | Plays well with FastAPI |
| Migrations | **Alembic** | Standard |
| DB | **SQLite** (single file) | MVP target; migrate to Postgres later |
| Queue | In-process asyncio queue + per-adapter semaphore | No Redis needed for MVP |
| Secrets | `keyring` (OS keychain) | No plaintext on disk |
| Dashboard | **React 18 + TypeScript + Vite** | User preference |
| Dashboard styling | **Tailwind CSS** + a tiny tokens file | Match prototype tokens 1:1 |
| Dashboard data | **TanStack Query** + native WebSocket | REST + live stream |
| Charts | **Recharts** (or hand-rolled SVG for the hourly bars) | Lightweight |
| Build/run | **Docker** + `docker-compose` | Single image with browsers |
| Deploy | Caddy reverse proxy w/ TLS in `compose.staging.yml` | One-line staging |

---

## Repo layout (target)

```
conduit/
├── apps/
│   ├── api/                       # Python — FastAPI service
│   │   ├── conduit/
│   │   │   ├── adapters/          # one file per provider
│   │   │   │   ├── base.py
│   │   │   │   ├── claude.py
│   │   │   │   ├── chatgpt.py
│   │   │   │   ├── deepseek.py
│   │   │   │   ├── grok.py
│   │   │   │   └── ollama.py
│   │   │   ├── api/               # FastAPI routers
│   │   │   │   ├── v1_chat.py     # OpenAI-compatible
│   │   │   │   ├── v1_messages.py # Anthropic-compatible alias
│   │   │   │   ├── adapters.py    # GET /adapters, POST /adapters/:id/relogin
│   │   │   │   ├── requests.py    # GET /requests (history), POST /requests/:id/replay
│   │   │   │   ├── templates.py
│   │   │   │   └── ws.py          # WebSocket /ws/live
│   │   │   ├── core/
│   │   │   │   ├── config.py      # pydantic-settings
│   │   │   │   ├── queue.py       # per-adapter semaphore queue
│   │   │   │   ├── routing.py     # cheapest/fastest/sticky/roundrobin
│   │   │   │   ├── tokens.py      # tiktoken + anthropic tokenizer
│   │   │   │   ├── pricing.py     # provider pricing table
│   │   │   │   └── budgets.py     # daily/monthly tracking + alerts
│   │   │   ├── db/
│   │   │   │   ├── models.py      # SQLModel models
│   │   │   │   ├── repos.py       # CRUD
│   │   │   │   └── seed.py        # mock seed
│   │   │   ├── stealth/           # playwright-extra config
│   │   │   ├── webhooks.py
│   │   │   └── main.py            # FastAPI app factory
│   │   ├── alembic/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   ├── dashboard/                 # React + Vite + TS — see prototype
│   │   ├── src/
│   │   │   ├── tokens.ts          # design tokens (mirror prototype C{})
│   │   │   ├── api.ts             # typed REST + WS client
│   │   │   ├── components/        # atoms, molecules
│   │   │   ├── views/             # one per tab (Live, History, …)
│   │   │   ├── App.tsx
│   │   │   └── main.tsx
│   │   ├── index.html
│   │   ├── tailwind.config.ts
│   │   ├── vite.config.ts
│   │   └── package.json
│   └── cli/                       # `conduit send`, `conduit ls`, `conduit replay`
│       └── pyproject.toml
├── docker-compose.yml             # local dev
├── docker-compose.staging.yml     # staging w/ Caddy + TLS
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ADAPTERS.md                # how to write a new adapter
│   ├── ROUTING.md
│   └── RUNBOOK.md
└── README.md
```

---

## Build phases

The plan is encoded in the prototype's **Roadmap** tab (`prototype/data.js → window.ROADMAP`). Read it there first — every phase has an `estMessages`, an `effort`, a target model (Sonnet 4.6 / Opus 4.7), and a `testable` exit criterion.

> **Working principle:** each phase is one Claude Code session. Each phase ends testable. No phase rolls over. Opus is reserved for architecture-locking phases (2: adapter pattern, 5: streaming, 7: routing).

| # | Name | Model | Done when… |
|---|---|---|---|
| 0 | Repo skeleton & Docker | Sonnet | `curl :8000/health` returns `{"ok":true}`; dashboard scaffolds on :5173 |
| 1 | Storage layer | Sonnet | pytest green on `tests/storage/`; sqlite browser shows seeded rows |
| 2 | Claude.ai adapter (MVP e2e) | **Opus** | `conduit send --adapter claude "hello"` returns text + DB row |
| 3 | OpenAI-compat REST + queue | Sonnet | `openai-python` client w/ `BASE_URL=localhost:8000` works |
| 4 | Dashboard skeleton (Live + History) | Sonnet | Send 5 curl requests → all appear live; refresh → history matches |
| 5 | Streaming + accurate token tracking | **Opus** | `curl -N` streams chunks; dashboard shows tokens-per-second meter |
| 6 | ChatGPT/DeepSeek/Grok/Ollama adapters | Sonnet | Same prompt to each adapter returns valid completion |
| 7 | Smart routing & guardrails | **Opus** | Force 429 on Claude → next request goes to ChatGPT; budget banner at 80% |
| 8 | Power features (compare, replay, templates, threads, webhooks, CLI) | Sonnet | Compare panel shows 3 responses; CLI replays request id; webhook fires |
| 9 | Staging deploy & docs | Sonnet | `curl https://conduit.<domain>/v1/chat/completions` from another machine |

See **`PHASES.md`** in this folder for full per-phase Claude Code prompts.

---

## Screens / Views

The dashboard has **9 tabs**, all visible in the sidebar. Detailed specs live in **`SCREENS.md`**. Quick index:

| Tab | Purpose | Key components |
|---|---|---|
| **Live** | Real-time stream of new requests | header metrics row, log table with row highlight on new entries, pause/resume |
| **History** | All past requests with filters | search bar, adapter filter, status filter, paginated log table |
| **Adapters** | Health & session state per provider | grid of adapter cards (status dot, queue, p95, success%, last error) |
| **Compose** | Manual prompt sender | prompt textarea, adapter+policy controls, response panel, this-run metrics |
| **Compare** | Fan one prompt to N adapters | adapter pickers, response columns side-by-side w/ latency+cost deltas |
| **Templates** | Prompt library with `{{vars}}` | left list, right preview with highlighted variables |
| **Cost** | Token/spend tracking & projection | totals, monthly budget bar, by-adapter breakdown, hourly stacked chart |
| **Roadmap** | Build phases (this exists in the dashboard itself for visibility) | timeline of phase cards w/ deliverables + testable criterion |
| **Settings** | API keys, routing defaults, budget, webhooks | sectioned form |

**Detail Drawer** (right slide-out, used from Live + History rows): prompt, response (with caret), timing breakdown bars (queue/navigate/send/gen/extract), tokens & cost metrics, action buttons (Replay, Replay on…, Copy as cURL, Save as template, View raw).

---

## Design tokens

Mirror these exactly in `apps/dashboard/src/tokens.ts` and your Tailwind config. They come from `prototype/components.jsx → const C`:

```ts
export const tokens = {
  color: {
    bg:        '#0b0d10',
    panel:     '#101317',
    panelHi:   '#14181d',
    panelLo:   '#0d1014',
    border:    '#1f242b',
    borderHi:  '#2a3038',
    text:      '#e4e7ec',
    textDim:   '#8a929c',
    textMute:  '#5a626c',
    accent:    '#7dd3fc',  // electric cyan, signature
    accentDim: '#0c4a6e',
    ok:        '#4ade80',
    warn:      '#fbbf24',
    err:       '#f87171',
    rate:      '#c084fc',  // 429 / rate-limit purple
  },
  // Per-provider brand colors (used in pills, charts, card top-borders)
  provider: {
    claude:   '#d97757',
    chatgpt:  '#10a37f',
    deepseek: '#4d6bfe',
    grok:     '#cccccc',
    ollama:   '#888888',
  },
  font: {
    sans: '"Inter", ui-sans-serif, system-ui, sans-serif',
    mono: '"JetBrains Mono", ui-monospace, SFMono-Regular, monospace',
  },
  radius: {
    sm: 3, md: 4, lg: 6,
  },
  // Spacing follows 4px grid; common values: 4 6 8 10 12 14 16 18 20 22 28
  // No box-shadows in this design — depth is conveyed via layered backgrounds + borders
};
```

**Typography rules:**
- All numbers, IDs, timestamps, code, file paths → **mono** (`JetBrains Mono`)
- All UI labels and prose → **sans** (`Inter`)
- Section labels (e.g. "prompt", "response", "timing"): mono, 10px, uppercase, `letter-spacing: 0.08em`, color `textMute`
- Body text: 12.5–13px sans
- Numbers in metrics: 16–18px mono
- H1 (page title): 22px sans, weight 500, `letter-spacing: -0.02em`

**Status colors:**
- `online` / `200 OK` / `done` → `ok` (#4ade80)
- `degraded` / `warn` / `in_progress` → `warn` (#fbbf24) or `accent` for active states
- `offline` / `error` → `err` (#f87171)
- `429` / `rate_limit` → `rate` (#c084fc)

**Motion:**
- Tab/hover transitions: `0.12s` ease
- Drawer slide-in: `0.22s cubic-bezier(.2,.8,.3,1)`
- Status dot pulse: 2s ease-out infinite (see `@keyframes pulse` in `components.jsx`)
- Generating cursor: 1s blink
- Fresh-row highlight on Live: 1.5s, then fades over 0.6s

---

## API contract (target)

### Public endpoints

```
POST  /v1/chat/completions       # OpenAI-compatible, supports stream=true
POST  /v1/messages               # Anthropic-compatible alias
GET   /v1/models                 # Lists available adapter models

GET   /api/adapters              # Health grid data
POST  /api/adapters/:id/relogin  # Trigger interactive login
POST  /api/adapters/:id/test     # Ping adapter

GET   /api/requests              # paginated, ?adapter=&status=&q=&from=&to=
GET   /api/requests/:id
POST  /api/requests/:id/replay   # body: { adapter?: string }

GET   /api/templates
POST  /api/templates
PATCH /api/templates/:id
DELETE /api/templates/:id

GET   /api/cost/today
GET   /api/cost/projection       # ?period=month

WS    /ws/live                   # streams new request events + token deltas
GET   /health
GET   /openapi.json              # auto from FastAPI
```

### Auth
Single API key in `Authorization: Bearer sk-cdt-…` header. Stored hashed in DB; raw value lives in OS keychain via `keyring`.

### `/v1/chat/completions` request
Identical to OpenAI. Conduit-specific extras go under `metadata`:
```json
{
  "model": "claude-sonnet-4.6",
  "messages": [...],
  "stream": true,
  "metadata": {
    "conduit": {
      "policy": "cheapest",       // override default routing
      "thread_id": "thr_abc",     // multi-turn continuity
      "tags": ["cursor", "review"]
    }
  }
}
```

### Routing policies
- `cheapest` — lowest projected cost on the *real* API for this prompt
- `fastest` — lowest p50 latency over last hour
- `sticky` — same adapter as last request in this thread
- `roundrobin` — distribute evenly
- `pinned` — use exactly the model field

---

## State management (dashboard)

- **Server state:** TanStack Query for everything REST. 5s stale time on lists; infinite stale on completed requests.
- **Live state:** single WebSocket connection on app mount. Events: `request:new`, `request:token`, `request:done`, `adapter:health`, `budget:alert`. Each event invalidates the relevant Query keys.
- **Local UI state:** `useState` per view — current filter, drawer open/closed, picked adapters in Compare. No global store needed.

---

## Adapters — how they work

Every provider is implemented as a class extending `BaseAdapter`:

```python
class BaseAdapter(ABC):
    id: str
    vendor: str
    model: str
    color: str

    async def login(self) -> None: ...           # interactive on first run
    async def is_authenticated(self) -> bool: ...
    async def send(self, messages: list[dict], *, stream: bool) -> AsyncIterator[Chunk]: ...
    async def health(self) -> AdapterHealth: ...
    async def close(self) -> None: ...
```

Each adapter owns a persistent `BrowserContext` with a per-adapter `userDataDir` so login survives restarts. `playwright-stealth` is applied to every page. Selector strategy:
1. Prefer `data-*` attributes
2. Fallback to ARIA roles + accessible names
3. Visible-text selectors only as last resort
4. **Never** raw CSS classes (these change frequently on AI provider sites)

Errors capture a screenshot to `var/screenshots/<request_id>.png` (auto-scrubbed for PII before storage if `ENV=production`).

See **`ADAPTERS.md`** in this folder for the per-provider DOM probes and known gotchas.

---

## Files in this handoff

```
design_handoff_conduit/
├── README.md           ← you are here
├── PHASES.md           ← detailed Claude Code prompts, one per phase
├── SCREENS.md          ← per-screen specs (layout, components, copy)
├── ADAPTERS.md         ← provider-specific notes & DOM strategy
└── prototype/
    ├── Conduit.html    ← entry — open in a browser to see the design
    ├── app.jsx         ← root + tab routing + Tweaks panel
    ├── components.jsx  ← atoms (StatusDot, Tag, AdapterPill, LogRow, DetailDrawer, …)
    ├── views-1.jsx     ← Live, History, Adapters
    ├── views-2.jsx     ← Compose, Compare, Templates, Cost, Plan, Settings
    ├── data.js         ← mock data + ROADMAP + PROVIDER_PRICING
    └── tweaks-panel.jsx
```

**To preview the prototype:** open `prototype/Conduit.html` in a modern browser (Chrome / Firefox). All assets are CDN-loaded; no build step needed.
