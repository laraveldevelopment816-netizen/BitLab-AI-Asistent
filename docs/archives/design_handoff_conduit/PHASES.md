# Phases — Claude Code prompts

One phase = one Claude Code session. Each phase is **fully testable** before you move on.

> **How to use this file:** copy the entire prompt for the phase you're starting and paste it into Claude Code. It includes the model recommendation, the deliverables, and the exit criterion.

---

## Phase 0 — Repo skeleton & Docker
**Model:** Sonnet 4.6 · **Effort:** low · **Est:** ~12 messages

```text
You are starting a new project called Conduit. Read design_handoff_conduit/README.md
first to understand the architecture, then scaffold the repo per the layout in that
README.

Specifically in this session:
1. Initialise the monorepo: apps/api (Python 3.12 + Poetry), apps/dashboard
   (Vite + React + TS), apps/cli (Python). Root has docker-compose.yml.
2. apps/api Dockerfile based on `mcr.microsoft.com/playwright-python:v1.48.0-noble`.
   FastAPI app with a single endpoint: GET /health → {"ok": true, "version": "0.1.0"}.
3. apps/dashboard scaffolded with Vite + React 18 + TS + Tailwind. Configure
   Tailwind theme to mirror tokens from design_handoff_conduit/README.md
   (Design tokens section). Render a single page with the Conduit wordmark and
   "v0.1.0" so we can see fonts loaded correctly.
4. pre-commit with ruff + black + mypy on apps/api.
5. pytest skeleton at apps/api/tests/test_health.py asserting /health returns 200.
6. README.md at repo root with `docker compose up` instructions.

DONE WHEN:
- `docker compose up` brings both services up cleanly
- `curl localhost:8000/health` returns the JSON above
- Browser at localhost:5173 shows the wordmark in JetBrains Mono
- `cd apps/api && pytest` is green
```

---

## Phase 1 — Storage layer
**Model:** Sonnet 4.6 · **Effort:** medium · **Est:** ~18 messages

```text
Building on Phase 0 of Conduit. We now add the persistence layer.

Read design_handoff_conduit/README.md if not already in context.

In apps/api:
1. Add SQLModel + Alembic. Configure for SQLite at `var/conduit.db` (gitignored).
2. Models (SQLModel):
   - Adapter(id, name, vendor, model, color, userDataDir, status, last_error,
     created_at, updated_at)
   - Request(id, adapter_id, model, prompt_text, messages_json, client, status,
     tokens_in, tokens_out, latency_s, cost_usd, thread_id, replay_of_id,
     created_at, completed_at)
   - Response(id, request_id, text, raw_html_snapshot, screenshot_path)
   - ErrorLog(id, request_id, kind, message, stack, screenshot_path, created_at)
   - Template(id, name, body, tags_json, uses, created_at, updated_at)
   - Thread(id, title, adapter_id, created_at, last_message_at)
3. Alembic migration `0001_initial.py`.
4. Async repos in conduit/db/repos.py — RequestRepo, AdapterRepo, TemplateRepo
   with type-safe pagination + filtering.
5. Seed script (`python -m conduit.db.seed`) that creates 5 adapters and ~40
   realistic requests. Use the mock data shape from prototype/data.js as a
   reference for realistic prompts/responses/token counts.
6. Tests at apps/api/tests/storage/ — must hit >85% coverage on the storage
   module. Use pytest-asyncio.

DONE WHEN:
- `alembic upgrade head` creates the schema
- `python -m conduit.db.seed` populates rows
- `pytest tests/storage/ --cov=conduit.db --cov-report=term` ≥ 85%
- `sqlite3 var/conduit.db "SELECT count(*) FROM request"` returns 40
```

---

## Phase 2 — Claude.ai adapter (MVP end-to-end)  ⭐ Opus
**Model:** Opus 4.7 · **Effort:** high · **Est:** ~32 messages

> Use Opus here. This phase locks in the adapter pattern that all other adapters
> will copy. A wobbly abstraction here costs us 4 phases later.

```text
Building on Phase 1 of Conduit. We now add the FIRST adapter and prove
end-to-end: prompt in → response out, persisted to DB.

Read design_handoff_conduit/README.md AND design_handoff_conduit/ADAPTERS.md
before starting.

1. apps/api/conduit/adapters/base.py — BaseAdapter ABC with the contract
   defined in README.md ("Adapters — how they work" section). Include:
   - AsyncIterator[Chunk] return from .send() (Chunk = {text, tokens_in_delta,
     tokens_out_delta, finished, raw_event})
   - AdapterHealth dataclass
2. Persistent BrowserContext per adapter under `var/profiles/<adapter_id>/`.
   Use playwright async + playwright-stealth.
3. Build conduit/adapters/claude.py. The session is at https://claude.ai.
   - Detect login state by probing for the composer
   - If not authenticated → mark adapter status='needs_auth', emit a
     webhook-shaped log event, raise NeedsAuthError
   - Send a message: locate the composer (data-* preferred, role fallback),
     paste prompt, click send
   - Wait for stop button to disappear (= generation complete)
   - Extract the last assistant message text via stable selectors
   - Take screenshot on every error before re-raising
4. Token counting: input via anthropic-tokenizer-python; output via the same.
   Both exact, not estimates.
5. CLI: `apps/cli/conduit/main.py` with one command:
   `conduit send --adapter claude "your prompt"` → prints response, prints
   `tokens: ↓N ↑M · latency: Xs · cost: $Y.YYYY` summary, persists to DB.
6. Pricing table at apps/api/conduit/core/pricing.py — copy from
   prototype/data.js → window.PROVIDER_PRICING.

CRITICAL: do not screen-scrape with class selectors. Document the selector
strategy in conduit/adapters/claude.py at the top.

DONE WHEN:
- `conduit send --adapter claude "Reply with the word PONG."` prints PONG
- A row appears in DB with non-zero tokens_in, tokens_out, latency_s, cost_usd
- Logging out of Claude.ai then re-running gives a friendly "needs auth" msg,
  not a stack trace
- One pytest integration test using a recorded HAR fixture
```

---

## Phase 3 — OpenAI-compatible REST + queue
**Model:** Sonnet 4.6 · **Effort:** high · **Est:** ~26 messages

```text
Building on Phase 2 of Conduit. We expose the adapter via an HTTP API
that any OpenAI client can talk to.

Read design_handoff_conduit/README.md "API contract" section.

1. Routers:
   - POST /v1/chat/completions (NON-streaming for now; stream=true returns 501)
   - POST /v1/messages (Anthropic-compat alias — translates to/from same store)
   - GET /v1/models
   - GET /api/adapters, GET /api/requests with pagination + filters
2. In-process queue (conduit/core/queue.py): asyncio.Queue per adapter, plus a
   semaphore with default concurrency=1 per adapter (configurable).
   Backpressure: if queue depth > 50, return 429 with Retry-After.
3. API key auth middleware. Single key in env `CONDUIT_API_KEY`, hashed
   comparison. Hash stored in DB on first start.
4. Request lifecycle persisted with full timing breakdown:
   queued_at, navigation_started_at, send_started_at, generation_started_at,
   generation_completed_at, extracted_at.
5. FastAPI auto-generates OpenAPI at /openapi.json.
6. Update CLI: `conduit send` now hits the HTTP API instead of calling the
   adapter directly. CLI reads CONDUIT_API_KEY from env or keychain.

DONE WHEN:
- This Python script works:
    from openai import OpenAI
    c = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-cdt-...")
    print(c.chat.completions.create(
        model="claude-sonnet-4.6",
        messages=[{"role":"user","content":"reply with PONG"}]
    ).choices[0].message.content)
- Spam 100 concurrent requests → server returns 429 with Retry-After before
  hanging
- DB Request rows have all 6 timing columns populated
```

---

## Phase 4 — Dashboard skeleton (Live + History)
**Model:** Sonnet 4.6 · **Effort:** medium · **Est:** ~22 messages

```text
Building on Phase 3 of Conduit. We now build the dashboard.

REFERENCE: prototype/Conduit.html in design_handoff_conduit/. Match colors,
typography, spacing, micro-interactions to the prototype. Use Tailwind with
tokens from README.md → Design tokens.

In apps/dashboard:
1. Layout: sidebar (per Sidebar component in prototype) + main + drawer.
   Sidebar items shown for now: Live, History, Adapters, Cost. Stub the
   others with "coming in phase X".
2. TanStack Query + native WebSocket client (apps/dashboard/src/api.ts).
3. Live tab: WS subscription, log table matching prototype's LogRow, fresh-row
   highlight (1.5s background, 0.6s fade).
4. History tab: paginated, filter by adapter / status, full-text search.
5. Detail drawer: prompt, response, timing breakdown bars, tokens & cost.
   Match prototype DetailDrawer exactly.
6. Adapters tab: cards per AdapterCard in prototype.

Backend additions needed:
- WS endpoint /ws/live broadcasting events (request:new, request:done)
- GET /api/cost/today aggregate

DONE WHEN:
- Open dashboard, send 5 requests via curl in another terminal
- All 5 appear in Live in real time (no refresh)
- Refresh → History shows the same 5
- Click any row → drawer slides in with full detail
- Adapters tab shows the Claude card with green status dot
```

---

## Phase 5 — Streaming + accurate token tracking  ⭐ Opus
**Model:** Opus 4.7 · **Effort:** high · **Est:** ~30 messages

> Use Opus. The streaming protocol mapping (browser MutationObserver →
> Anthropic message_start/delta/stop → SSE → OpenAI choices.delta) is the
> trickiest reasoning of the project. Do it once.

```text
Building on Phase 4 of Conduit. We now stream tokens as they arrive.

1. In Claude adapter: switch from "wait until done, then extract" to a
   MutationObserver-based incremental extractor. The browser side runs a small
   `init script` that emits CustomEvents on each new text chunk; Playwright
   binds to those via expose_function.
2. Map the chunks to Anthropic-style message events
   (message_start, content_block_delta, message_stop) AND OpenAI-style
   chunks (choices[0].delta.content) — both at once, since both endpoints share
   the same internal stream.
3. POST /v1/chat/completions with stream=true returns SSE.
4. Per-token timestamping: store deltas as JSONL alongside the Request row
   for analysis.
5. Wire the WS event request:token to the dashboard. Add a tokens-per-second
   meter to the Live tab and the detail drawer.

DONE WHEN:
- `curl -N` against /v1/chat/completions with stream=true streams chunks as
  they're generated (visually obvious in terminal)
- Dashboard shows live tps meter when a request is in-flight
- DB has per-token timing data for at least one request
```

---

## Phase 6 — More adapters
**Model:** Sonnet 4.6 · **Effort:** high · **Est:** ~28 messages

```text
Building on Phase 5 of Conduit. Add: ChatGPT, DeepSeek, Grok, Ollama.

Read design_handoff_conduit/ADAPTERS.md for per-provider DOM notes.

For each browser-based adapter (ChatGPT, DeepSeek, Grok):
- Subclass BaseAdapter
- Reuse the streaming MutationObserver pattern from Claude
- Cloudflare-aware login: if a CF challenge is detected on send, mark adapter
  status='cf_challenge' and surface in dashboard
- Record one HAR fixture per adapter for integration tests

Ollama is special — no browser. Native HTTP to localhost:11434 (or
OLLAMA_HOST env). Maps cleanly to the Chunk protocol.

DONE WHEN:
- Same prompt routed to each adapter via API returns valid completion
- Each has at least one passing integration test using HAR fixture
- Adapters tab in dashboard shows all 5 cards with correct branding colors
```

---

## Phase 7 — Smart routing & guardrails  ⭐ Opus
**Model:** Opus 4.7 · **Effort:** medium · **Est:** ~20 messages

```text
Building on Phase 6 of Conduit. Add the brain.

1. conduit/core/routing.py with policies: cheapest, fastest, sticky,
   roundrobin, pinned. Selection takes (messages, available_adapters,
   policy, thread_state) → adapter_id.
   - cheapest: estimate tokens, multiply by pricing table, pick min
   - fastest: pick adapter with lowest p50 latency in last 1h
   - sticky: same adapter as the last request in this thread_id
2. Rate-limit detector: when an adapter returns 429-equivalent (a known
   "you've hit your limit" message in the DOM, listed in ADAPTERS.md per
   provider), mark it cooldown=15min and re-route the in-flight request to
   the next-best adapter under the active policy.
3. Health scoring: rolling success rate over last 50 requests.
   <80% → auto-suspend the adapter; surface a banner.
4. Daily/monthly budget tracking. Soft limits in settings. Webhook +
   dashboard banner at 80%; refuse new requests at 100% (configurable).

DONE WHEN:
- Force a 429 on Claude (mock by patching `is_rate_limited()` in tests) →
  next request goes to ChatGPT automatically
- Set monthly budget to $1, run a few requests → banner appears at 80% spent
- Pytest covers each routing policy decision
```

---

## Phase 8 — Power features
**Model:** Sonnet 4.6 · **Effort:** medium · **Est:** ~24 messages

```text
Building on Phase 7 of Conduit. The cherry on top.

1. Compare mode: POST /api/compare { prompt, adapters: [..] } → fan-out,
   stream all responses. Dashboard view per CompareView in prototype.
2. Replay: POST /api/requests/:id/replay with optional adapter override.
3. Templates: full CRUD + Jinja2 var substitution. UI per TemplatesView.
4. Conversation threads: thread_id on requests, /api/threads list +
   /api/threads/:id messages. Sticky routing inside a thread.
5. Webhooks: register URLs in settings; fire on completion / error /
   budget-alert with HMAC signing.
6. CLI: `conduit ls`, `conduit replay <id>`, `conduit threads`,
   `conduit template apply <name> --var foo=bar`.
7. Encrypt API key + provider cookies via OS keychain (`keyring`). The DB
   stores only references.

DONE WHEN:
- Compare panel shows 3 streamed responses simultaneously
- `conduit replay req_abc123 --adapter chatgpt` works
- Webhook receiver sees a signed POST on completion
- After restart, no plaintext secrets exist on disk
```

---

## Phase 9 — Staging deploy & docs
**Model:** Sonnet 4.6 · **Effort:** low · **Est:** ~14 messages

```text
Building on Phase 8 of Conduit. Ship it.

1. docker-compose.staging.yml with three services: api, dashboard (built
   static), caddy (reverse proxy + auto TLS via Let's Encrypt).
2. Persistent volumes for var/profiles (browser sessions) and var/conduit.db.
3. Caddyfile routing /v1/* and /api/* to api:8000, /ws/* to api:8000 with
   websocket upgrade, everything else to dashboard:80.
4. Healthchecks + restart: unless-stopped.
5. docs/ARCHITECTURE.md, docs/RUNBOOK.md (how to relogin a stuck adapter
   remotely via temp X server forward), docs/ADAPTERS.md.
6. Bruno collection at docs/bruno/.

DONE WHEN:
- Deploy to a fresh VPS: clone, fill .env, `docker compose -f
  docker-compose.staging.yml up -d`
- `curl https://conduit.<your-domain>/v1/chat/completions` returns a
  completion from a remote machine
- Dashboard accessible at https://conduit.<your-domain>/
```
