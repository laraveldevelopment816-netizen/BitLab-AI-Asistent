// Mock data for Conduit dashboard prototype
// Real prices per 1M tokens (May 2026 estimates), used for cost projection
window.PROVIDER_PRICING = {
  'claude-sonnet-4.6':  { in: 3.00,  out: 15.00, label: 'Claude Sonnet 4.6',  vendor: 'Anthropic' },
  'claude-opus-4.7':    { in: 15.00, out: 75.00, label: 'Claude Opus 4.7',    vendor: 'Anthropic' },
  'gpt-5':              { in: 2.50,  out: 10.00, label: 'GPT-5',              vendor: 'OpenAI' },
  'gpt-5-mini':         { in: 0.25,  out: 2.00,  label: 'GPT-5 mini',         vendor: 'OpenAI' },
  'deepseek-v3':        { in: 0.27,  out: 1.10,  label: 'DeepSeek V3',        vendor: 'DeepSeek' },
  'grok-4':             { in: 5.00,  out: 15.00, label: 'Grok 4',             vendor: 'xAI' },
  'llama-3.3-70b':      { in: 0.00,  out: 0.00,  label: 'Llama 3.3 70B (local)', vendor: 'Ollama' },
};

window.ADAPTERS = [
  {
    id: 'claude',
    name: 'Claude.ai',
    vendor: 'Anthropic',
    model: 'claude-sonnet-4.6',
    status: 'online',
    auth: 'authenticated',
    sessionAge: '4d 12h',
    queueDepth: 0,
    activeRequests: 1,
    avgLatency: 4.2,
    p95Latency: 8.1,
    successRate: 99.4,
    requestsToday: 142,
    tokensToday: { in: 84200, out: 31600 },
    color: '#d97757',
    lastError: null,
  },
  {
    id: 'chatgpt',
    name: 'ChatGPT',
    vendor: 'OpenAI',
    model: 'gpt-5',
    status: 'online',
    auth: 'authenticated',
    sessionAge: '2d 03h',
    queueDepth: 2,
    activeRequests: 1,
    avgLatency: 3.8,
    p95Latency: 7.4,
    successRate: 98.7,
    requestsToday: 98,
    tokensToday: { in: 51200, out: 22400 },
    color: '#10a37f',
    lastError: null,
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    vendor: 'DeepSeek',
    model: 'deepseek-v3',
    status: 'online',
    auth: 'authenticated',
    sessionAge: '6d 18h',
    queueDepth: 0,
    activeRequests: 0,
    avgLatency: 2.1,
    p95Latency: 4.6,
    successRate: 99.8,
    requestsToday: 67,
    tokensToday: { in: 38900, out: 14200 },
    color: '#4d6bfe',
    lastError: null,
  },
  {
    id: 'grok',
    name: 'Grok',
    vendor: 'xAI',
    model: 'grok-4',
    status: 'degraded',
    auth: 'authenticated',
    sessionAge: '0d 04h',
    queueDepth: 1,
    activeRequests: 0,
    avgLatency: 6.7,
    p95Latency: 14.2,
    successRate: 91.2,
    requestsToday: 23,
    tokensToday: { in: 12400, out: 5800 },
    color: '#cccccc',
    lastError: 'Cloudflare challenge detected on send (auto-recovered)',
  },
  {
    id: 'ollama',
    name: 'Ollama (local)',
    vendor: 'Local',
    model: 'llama-3.3-70b',
    status: 'offline',
    auth: 'n/a',
    sessionAge: '—',
    queueDepth: 0,
    activeRequests: 0,
    avgLatency: 0,
    p95Latency: 0,
    successRate: 0,
    requestsToday: 0,
    tokensToday: { in: 0, out: 0 },
    color: '#888888',
    lastError: 'Connection refused on http://localhost:11434',
  },
];

// Generate ~40 mock requests with a realistic distribution
function genRequests() {
  const prompts = [
    { p: 'Refactor this React component to use hooks', tokIn: 412, tokOut: 1840 },
    { p: 'Explain the difference between SSE and WebSockets', tokIn: 84, tokOut: 720 },
    { p: 'Write a Playwright script that logs into Gmail', tokIn: 96, tokOut: 1240 },
    { p: 'Summarize this PDF in 3 bullets', tokIn: 8400, tokOut: 180 },
    { p: 'Generate SQL for a leaderboard query', tokIn: 240, tokOut: 540 },
    { p: 'Review this PR diff and flag risks', tokIn: 3200, tokOut: 980 },
    { p: 'Translate to Serbian: …', tokIn: 1100, tokOut: 1080 },
    { p: 'Write unit tests for the queue module', tokIn: 1840, tokOut: 2400 },
    { p: 'Why is my Docker build slow?', tokIn: 320, tokOut: 1420 },
    { p: 'Draft a release note for v0.4', tokIn: 180, tokOut: 460 },
    { p: 'Compare Postgres vs SQLite for this workload', tokIn: 220, tokOut: 1640 },
    { p: 'Find the bug in this Python async code', tokIn: 940, tokOut: 720 },
  ];
  const adapters = ['claude', 'chatgpt', 'deepseek', 'grok'];
  const statuses = ['ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'ok', 'error', 'rate_limit', 'ok'];
  const out = [];
  const now = Date.now();
  for (let i = 0; i < 42; i++) {
    const prompt = prompts[i % prompts.length];
    const adapter = adapters[Math.floor(Math.random() * adapters.length)];
    const status = statuses[Math.floor(Math.random() * statuses.length)];
    const ts = now - i * (60_000 + Math.random() * 240_000);
    const latency = (1.2 + Math.random() * 6).toFixed(2);
    const wobble = 0.85 + Math.random() * 0.3;
    out.push({
      id: `req_${(99213 - i).toString(36)}`,
      ts,
      adapter,
      model: window.ADAPTERS.find(a => a.id === adapter).model,
      prompt: prompt.p,
      tokensIn:  Math.round(prompt.tokIn  * wobble),
      tokensOut: status === 'ok' ? Math.round(prompt.tokOut * wobble) : 0,
      latency: parseFloat(latency),
      status,
      response: status === 'ok'
        ? 'Sure — here is a refactored version using `useState` and `useEffect`. The key change is moving the data-fetching side effect into useEffect with a proper cleanup function…'
        : (status === 'rate_limit' ? 'Rate limited by provider. Retry queued.' : 'Selector did not resolve within 30s. Screenshot saved.'),
      cost: 0, // computed below
      client: ['cursor', 'continue.dev', 'curl', 'conduit-cli', 'web-dashboard'][i % 5],
    });
  }
  // compute cost
  for (const r of out) {
    const p = window.PROVIDER_PRICING[r.model];
    if (p) r.cost = (r.tokensIn * p.in + r.tokensOut * p.out) / 1_000_000;
  }
  return out;
}
window.REQUESTS = genRequests();

// Hourly token usage for last 24h, per adapter
window.HOURLY = (() => {
  const out = [];
  for (let h = 23; h >= 0; h--) {
    const row = { hour: h };
    for (const a of window.ADAPTERS) {
      if (a.status === 'offline') { row[a.id] = 0; continue; }
      const base = a.requestsToday / 24;
      row[a.id] = Math.max(0, Math.round(base * (0.4 + Math.random() * 1.6)));
    }
    out.push(row);
  }
  return out.reverse();
})();

// Saved prompt templates
window.TEMPLATES = [
  { id: 't1', name: 'Code review', body: 'Review the following diff. Flag bugs, security issues, and style problems. Be terse.\n\n{{diff}}', tags: ['dev', 'review'], uses: 84 },
  { id: 't2', name: 'Commit message', body: 'Write a conventional commit message for this diff:\n\n{{diff}}', tags: ['dev', 'git'], uses: 142 },
  { id: 't3', name: 'Translate to Serbian', body: 'Translate to natural Serbian (latin script):\n\n{{text}}', tags: ['lang'], uses: 31 },
  { id: 't4', name: 'Explain like I\'m senior', body: 'Explain {{topic}} concisely to a senior engineer. No fluff.', tags: ['learn'], uses: 56 },
  { id: 't5', name: 'SQL from spec', body: 'Write Postgres SQL for: {{spec}}\n\nReturn only the query, no commentary.', tags: ['dev', 'sql'], uses: 22 },
];

// Roadmap — used by Plan tab
window.ROADMAP = [
  {
    id: 0, name: 'Repo skeleton & Docker',
    model: 'Sonnet 4.6', effort: 'low',
    status: 'done',
    deliverables: [
      'Python 3.12 + Poetry project',
      'Dockerfile based on mcr.microsoft.com/playwright:v1.48.0-noble',
      'docker-compose.yml (api + dashboard)',
      'FastAPI hello-world on /health',
      'Vite + React + TS dashboard scaffold',
      'pre-commit + ruff + black + pytest skeleton',
    ],
    testable: 'curl localhost:8000/health → {"ok":true}; dashboard loads on :5173',
    estMessages: 12,
  },
  {
    id: 1, name: 'Storage layer',
    model: 'Sonnet 4.6', effort: 'medium',
    status: 'done',
    deliverables: [
      'SQLModel schema: requests, responses, adapters, errors, templates, threads',
      'Alembic migrations',
      'CRUD repositories with async session',
      'Seed script with realistic mock data',
      'pytest coverage > 85% on storage module',
    ],
    testable: 'pytest tests/storage/ green; sqlite browser shows seeded rows',
    estMessages: 18,
  },
  {
    id: 2, name: 'Claude.ai adapter (MVP end-to-end)',
    model: 'Opus 4.7', effort: 'high',
    status: 'in_progress',
    deliverables: [
      'BaseAdapter abstract class (login, send, scrape, health, close)',
      'Persistent BrowserContext with userDataDir per adapter',
      'playwright-stealth integration',
      'Selector strategy doc (data-* preferred, role-based fallback, text last)',
      'ClaudeAdapter: detect login state, send prompt, wait-for-stop, extract text',
      'Token estimator (tiktoken/anthropic-tokenizer) — input exact, output exact',
      'Screenshot-on-error with PII scrubbing',
    ],
    testable: 'CLI: `conduit send --adapter claude "hello"` → text response + tokens logged in DB',
    estMessages: 32,
  },
  {
    id: 3, name: 'OpenAI-compatible REST + queue',
    model: 'Sonnet 4.6', effort: 'high',
    status: 'todo',
    deliverables: [
      'POST /v1/chat/completions (non-streaming)',
      'POST /v1/messages (Anthropic alias)',
      'In-memory queue + per-adapter concurrency lock',
      'Backpressure (429 with Retry-After when queue full)',
      'API key auth (single key in env, hashed)',
      'Request/response persisted with full timing breakdown',
      'OpenAPI spec auto-generated by FastAPI',
    ],
    testable: 'openai-python client points BASE_URL to localhost:8000 and works',
    estMessages: 26,
  },
  {
    id: 4, name: 'Dashboard skeleton — Live + History',
    model: 'Sonnet 4.6', effort: 'medium',
    status: 'todo',
    deliverables: [
      'Layout: sidebar + main + detail drawer',
      'Live tab: WebSocket stream of new requests',
      'History tab: paginated, filter by adapter/status/date/client',
      'Request detail drawer: prompt, response, timings, screenshots, raw HTML',
      'Adapters tab: health grid (status, queue, latency, errors)',
    ],
    testable: 'Open dashboard, send 5 requests via curl → all appear live; refresh and history matches',
    estMessages: 22,
  },
  {
    id: 5, name: 'Streaming + accurate token tracking',
    model: 'Opus 4.7', effort: 'high',
    status: 'todo',
    deliverables: [
      'MutationObserver-based incremental scraping per adapter',
      'SSE endpoint /v1/chat/completions (stream=true)',
      'Per-token timestamp logging',
      'Anthropic message_start/delta/stop event mapping',
      'Token counters wired live to dashboard via WS',
    ],
    testable: 'curl with -N streams chunks; dashboard shows tokens-per-second meter',
    estMessages: 30,
  },
  {
    id: 6, name: 'Adapters: ChatGPT, DeepSeek, Grok, Ollama',
    model: 'Sonnet 4.6', effort: 'high',
    status: 'todo',
    deliverables: [
      'ChatGPTAdapter (with Cloudflare-aware login flow)',
      'DeepSeekAdapter',
      'GrokAdapter',
      'OllamaAdapter (no browser, native HTTP — fallback path)',
      'Per-adapter integration tests with recorded HAR fixtures',
    ],
    testable: 'Same prompt routed to each adapter returns valid completion',
    estMessages: 28,
  },
  {
    id: 7, name: 'Smart routing & guardrails',
    model: 'Opus 4.7', effort: 'medium',
    status: 'todo',
    deliverables: [
      'Routing policies: cheapest, fastest, round-robin, sticky-session, model-pinned',
      'Rate-limit detector with exponential backoff and adapter switch',
      'Daily/monthly budget alerts (webhook + dashboard banner)',
      'Adapter health scoring with auto-suspension after N failures',
    ],
    testable: 'Force 429 on Claude → next request goes to ChatGPT; budget banner shows when 80% spent',
    estMessages: 20,
  },
  {
    id: 8, name: 'Power features',
    model: 'Sonnet 4.6', effort: 'medium',
    status: 'todo',
    deliverables: [
      'Compare mode (fan-out same prompt to N adapters, side-by-side diff)',
      'Replay (re-run any historical request, optionally on different adapter)',
      'Prompt template library with {{vars}} and Jinja',
      'Conversation threads (multi-turn with persistent context)',
      'Webhooks on completion',
      'CLI tool: `conduit send`, `conduit ls`, `conduit replay <id>`',
      'Encrypted secrets via OS keychain (keyring lib)',
    ],
    testable: 'Compare panel shows 3 responses; CLI replays request id; webhook fires',
    estMessages: 24,
  },
  {
    id: 9, name: 'Staging deploy & docs',
    model: 'Sonnet 4.6', effort: 'low',
    status: 'todo',
    deliverables: [
      'docker-compose.staging.yml with Caddy reverse proxy + TLS',
      'Persistent volume for browser profiles + SQLite',
      'Healthcheck + auto-restart',
      'README, ARCHITECTURE.md, runbook',
      'Postman / Bruno collection',
    ],
    testable: 'curl https://conduit.<your-domain>/v1/chat/completions from another machine returns a completion',
    estMessages: 14,
  },
];
