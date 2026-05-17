# Adapters — provider-specific notes

This is field-guide content for whoever's writing or maintaining adapters. Selectors change; treat anything below as a starting probe, not gospel. **Always re-verify in DevTools before shipping**, and prefer accessible attributes over visual classes.

---

## Common contract

```python
class BaseAdapter(ABC):
    id: str            # "claude" | "chatgpt" | "deepseek" | "grok" | "ollama"
    vendor: str
    model: str
    color: str         # for UI pills/borders

    async def login(self, *, interactive: bool = True) -> None: ...
    async def is_authenticated(self) -> bool: ...
    async def send(
        self, messages: list[dict], *, stream: bool, abort: AbortSignal
    ) -> AsyncIterator[Chunk]: ...
    async def health(self) -> AdapterHealth: ...
    async def close(self) -> None: ...
```

`Chunk` shape:
```python
@dataclass
class Chunk:
    text: str                     # delta text since last chunk
    tokens_in_delta: int = 0      # usually 0 except in first chunk
    tokens_out_delta: int = 0
    finished: bool = False
    raw_event: dict | None = None # provider-native event for debugging
```

---

## Browser context strategy

Per adapter: one persistent `BrowserContext` with `userDataDir = var/profiles/<id>/`. This persists cookies, localStorage, and IndexedDB → login survives restarts.

Every page in every adapter:
1. Apply `playwright-stealth` (the Python port — `playwright-stealth==2.x`)
2. Set realistic viewport (1366×900) and locale (`en-US`)
3. Realistic user-agent (let stealth handle the patch — don't override)
4. Inject a CDP-bound expose_function `__conduit_chunk(payload)` that the in-page MutationObserver calls on each new text fragment

---

## Selector strategy (in priority order)

1. **`data-*` attributes** — most stable across deploys
2. **ARIA roles + accessible names** — `role="textbox"` + `aria-label`/placeholder text
3. **Stable test IDs** if the site exposes them
4. **Semantic tags + position** — last resort
5. **NEVER** raw CSS classes (`.css-1abc23xy`) — these change weekly

When you fall back to text selectors, hardcode the English-locale strings only. Force `Accept-Language: en` in context options so localized UIs don't break selectors.

---

## Cloudflare-aware login

ChatGPT, Claude.ai, Grok all sit behind Cloudflare Turnstile or similar. Detection probe (run on every navigation):

```python
async def detect_cf_challenge(page) -> bool:
    # Generic Turnstile / interstitial heuristics
    if await page.locator('iframe[src*="challenges.cloudflare.com"]').count() > 0:
        return True
    if 'just a moment' in (await page.title()).lower():
        return True
    return False
```

If detected during login → mark adapter `status='cf_challenge'`, surface in dashboard, require user attention. If detected mid-send → wait up to 30s for auto-resolve (often passive), then escalate.

---

## Per-provider notes

### Claude.ai (`id="claude"`)

- **URL:** `https://claude.ai/new`
- **Auth probe:** presence of `[data-testid="composer-textarea"]` or fall back to `[contenteditable="true"][role="textbox"]`. If redirected to `/login`, not authenticated.
- **Composer:** `contenteditable` div. Use `page.fill()` won't work — use `page.evaluate` to set `innerText` then dispatch `input` event, or use `keyboard.type` with a small delay (8–12ms per char).
- **Send:** button with `aria-label="Send Message"` (case may vary). Fallback: `Enter` key when composer focused.
- **Generation done:** the stop button (`aria-label="Stop generating"` or similar) disappears AND the last assistant message stops mutating for 250ms.
- **Response extraction (final):** the last `[data-testid="message-content"]` (or class with `data-is-streaming="false"`).
- **Streaming chunks:** observe MutationObserver on the assistant turn container; on each character/token the DOM mutates. Debounce at 30ms.
- **Token counting:** input via `anthropic-tokenizer` package; output same. Both exact, no estimation.
- **Rate-limit signal:** banner with text containing "you've reached your limit" or upgrade prompt overlay. Cooldown 1h is safe default.

### ChatGPT (`id="chatgpt"`)

- **URL:** `https://chatgpt.com`
- **Auth probe:** redirect to `/auth/login` means not authenticated. Otherwise composer present.
- **Composer:** `#prompt-textarea` (relatively stable test ID).
- **Send:** `[data-testid="send-button"]` — currently the most stable selector OpenAI ships.
- **Generation done:** send button re-enables AND stop-button (`[data-testid="stop-button"]`) disappears.
- **Response extraction:** last `[data-message-author-role="assistant"]` element. The text lives in nested markdown; serialize with `innerText` (preserves newlines reasonably).
- **Streaming chunks:** assistant message has class hint with `result-streaming` while in-flight; observe text mutations on its `.markdown` child.
- **Cloudflare:** common on first visit per day; Turnstile usually auto-solves with stealth.
- **Token counting:** input via `tiktoken` (`o200k_base` for GPT-5 family). Output by the same.
- **Rate-limit signal:** text "you've reached your free limit" / "rate limit" / 429 in network tab.

### DeepSeek (`id="deepseek"`)

- **URL:** `https://chat.deepseek.com`
- **Auth probe:** composer present. Login uses email/password — no Cloudflare.
- **Composer:** standard `<textarea>` — `page.fill()` works.
- **Send:** button next to composer, `role="button"` with name containing "send" or arrow icon.
- **Generation done:** send button re-enables; loading indicator disappears.
- **Response extraction:** last `.markdown` block in the conversation pane.
- **Streaming chunks:** clean — DOM appends text nodes incrementally, MutationObserver works without debounce.
- **Token counting:** DeepSeek publishes a tokenizer; use it via the `deepseek-tokenizer` package or fall back to tiktoken `cl100k_base` (≈±5% accurate).
- **Rate-limit signal:** Toast component with "rate limit" message.

### Grok (`id="grok"`)

- **URL:** `https://grok.com` (post-X-merger UI) or `https://x.com/i/grok`
- **Auth probe:** depends on entry point. From x.com requires X login; from grok.com may be standalone.
- **Composer:** complex — it's a textarea-styled `contenteditable`. Inspect `[data-testid="composer-input"]` first.
- **Send:** `[data-testid="composer-send-button"]`
- **Cloudflare:** rare but possible.
- **Streaming chunks:** Grok's UI animates token reveals — observe the assistant bubble's text content; chunks arrive cleanly.
- **Token counting:** xAI hasn't published a tokenizer. Use tiktoken `cl100k_base` as approximation; mark counts as estimated in metadata.
- **Rate-limit signal:** red banner. Cooldown unclear — start with 30min.

### Ollama (`id="ollama"`)

- **No browser.** Native HTTP via `httpx.AsyncClient`.
- **Endpoint:** `POST {OLLAMA_HOST}/api/chat` (default `http://localhost:11434`).
- **Streaming:** native NDJSON streaming on `?stream=true`; map directly to `Chunk`.
- **Auth:** none locally. If pointed at a remote Ollama (e.g. tailnet), bearer token may be configured.
- **Token counting:** Ollama returns `prompt_eval_count` and `eval_count` in the final response.
- **Health probe:** `GET /api/tags` returns model list.
- **Rate-limit:** N/A (local).
- **Why include it?** Free fallback when all browser adapters are rate-limited or in CF challenge.

---

## Anti-detection tactics (built in)

- `playwright-stealth` patches `navigator.webdriver`, plugin enumeration, languages, WebGL fingerprint, etc.
- Realistic timing: 8–12ms keystroke delays, 80–200ms pause between focus and type, 200–400ms before clicking send.
- Don't navigate fresh on every send — keep the conversation tab parked between requests when possible (reduces CF re-checks).
- Random viewport jitter on context creation: 1366±20 × 900±20.
- Use the same userDataDir for the life of the deploy — providers fingerprint device IDs and reset = suspicion.

---

## Error capture

On any exception:
1. Take a screenshot to `var/screenshots/<request_id>.png`
2. Save full DOM HTML to `var/snapshots/<request_id>.html`
3. Capture last 50 console messages and last 20 network requests via CDP
4. Persist `ErrorLog` row with: kind (NeedsAuth / CFChallenge / SelectorTimeout / RateLimit / Unknown), message, stack, paths to artifacts
5. If `ENV=production` → run a PII scrubber on screenshot (blur all text via OpenCV before storage)

---

## Recording HAR fixtures for tests

For each adapter:
1. `await context.tracing.start(snapshots=True, screenshots=True)`
2. Manually run a known prompt (`"Reply with the word PONG."`) end-to-end
3. `await context.tracing.stop(path=f"tests/fixtures/{adapter}_pong.zip")`

Tests load the trace and assert the adapter's send/extract logic produces "PONG". This lets us run integration tests offline in CI without browser sessions.

---

## When a provider's UI changes

This will happen. Workflow:
1. Live monitor `success_rate` per adapter; alert if drops <90% over 50 requests
2. Open `/api/adapters/:id/test` from dashboard — captures a fresh screenshot + DOM snapshot
3. Compare to last good snapshot (stored in git under `apps/api/conduit/adapters/_snapshots/`)
4. Update selectors. Bump adapter `version` in the class so old fixtures get re-recorded.
