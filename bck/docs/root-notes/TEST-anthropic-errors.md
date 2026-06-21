# Lokalno testiranje — Centralni Anthropic exception handler-i

Dev se diže direktno preko uvicorn-a u Python venv-u. URL je
`http://localhost:8000`.

## Pokretanje

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Ako je port 8000 zauzet (WSL2 + Docker Desktop proxy 8000-8090), dodaj
`--port 7777` i zamijeni URL u svim curl pozivima ispod.

## Test plan — Centralni exception handler (STATUS kartica `c4xh`)

Sve provjere moraju proći prije nego što se kartica vrati u Done ako se
mijenja kod handler-a. DoD izvor:
[`docs/plans/dod-chat-only.md`](docs/plans/dod-chat-only.md) sekcija 5,
edge case "Kada provider nema kredita".

### 1. Pytest unit testovi (primarno)

```bash
.venv/bin/python -m pytest tests/test_anthropic_error_handlers.py -v
```

Očekivano: **7 passed**. Pokriva sve scenarije bez trošenja pravog
Anthropic API-ja:

- `test_authentication_error_returns_503` — AuthError → 503
- `test_internal_server_error_returns_503` — Anthropic 5xx → 503
- `test_quota_credit_balance_returns_402_with_escalation` — quota → 402 + tel/email
- `test_quota_billing_keyword_also_triggers_402` — heuristika `billing`
- `test_quota_keyword_also_triggers_402` — heuristika `quota`
- `test_connection_error_returns_503_with_network_message` — mreža → 503
- `test_happy_path_unaffected_by_handlers` — 200 flow nije pokvaren

### 2. Happy path uživo (sanity check)

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Imate li laptop do 2000 KM?"}' | jq .reply
```

Očekivano: HTTP 200, smislen `reply`. Ovo dokazuje da registrovanje
handler-a nije slomilo postojeći flow.

### 3. AuthenticationError uživo (najjednostavniji manuelni trigger)

Zaustavi uvicorn. Privremeno postavi pogrešan API key:

```bash
ANTHROPIC_API_KEY=sk-ant-invalid uvicorn app.main:app --reload
```

```bash
curl -i -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}'
```

Očekivano:

- **HTTP status:** `503 Service Unavailable` (NE 500, NE 200)
- **Body:** `{"error":"ai_unavailable","reply":"Žao mi je, AI servis privremeno nije dostupan. ..."}`
- **Server log:** `ERROR ... Anthropic APIStatusError @ /api/chat (status=401): ...`
  praćeno full traceback-om (`exc_info=True`). Stack trace NE smije izaći u
  HTTP response — samo u log.

Restore: vrati pravi `ANTHROPIC_API_KEY` u `.env` i restartuj uvicorn.

### 4. Widget render — korisnik vidi `reply` umjesto generičke poruke

Sa pogrešnim API key-om iz koraka 3 i dalje aktivnim, otvori
`http://localhost:8000/` u browser-u, hard-reload (Ctrl+Shift+R),
otvori chat i pošalji bilo koju poruku.

Očekivano u widget-u:

- Bot poruka glasi *"Žao mi je, AI servis privremeno nije dostupan. Pokušajte za par minuta ili nas kontaktirajte na 066 516 174."*
- **NE** *"Greška servera. Pokušaj ponovo."* (to bi značilo da widget
  ignoriše `data.reply` na non-200 odgovorima — promjena u
  `public/widget.js:1345-1357` nije aktivna ili je cache-ovana).

Mehanizam: server vraća HTTP 503 sa JSON-om koji sadrži `reply` polje
sa user-friendly porukom. Widget u `sendMessage()` čita `data.reply`
prije fallback-a na generičku poruku.

### 5. Quota scenario (opciono, ne troši kredit)

Quota slučaj je teško pokrenuti uživo bez stvarnog trošenja kredita, pa
se oslanja primarno na unit testove (`test_quota_*` u koraku 1). Ako se
ipak desi u produkciji:

- HTTP status: 402
- Body: `{"error":"ai_quota_exhausted","reply":"Trenutno imamo tehnički zastoj... 066 516 174 ... prodaja@bitlab.rs"}`
- Widget prikazuje tačno tu poruku sa telefonom i email-om.

Heuristika prepoznaje quota po ključnim riječima `credit balance`,
`billing` ili `quota` u tekstu poruke koju vrati Anthropic SDK.

## Mehanizam — gdje šta sjedi

Dva sloja:

1. **Lokalni hvatač** (`app/agent.py:179, 203`) — primarni put.
   `try/except` oko `client.messages.create()` hvata
   `BadRequestError` / `RateLimitError` / `APIConnectionError` na call site-u
   i vraća HTTP 200 sa `_graceful_return(...)` (`ChatResponse` shape).
   Ovi slučajevi NE dolaze do centralnog handler-a.

2. **Centralni safety net** (`app/main.py:60-118`) — fallback put.
   `@app.exception_handler(anthropic.APIStatusError)` i
   `@app.exception_handler(anthropic.APIConnectionError)` hvataju ono
   što agent.py propusti — `AuthenticationError`, `PermissionDeniedError`,
   `InternalServerError`, generic `APIStatusError`, plus mrežne greške ako
   bi preskočile lokalni handler. Vraćaju 402 (quota) ili 503 (ostalo) sa
   `{"error": ..., "reply": ...}` JSON-om. Full trace u
   `logger.error(..., exc_info=True)`.

Widget (`public/widget.js:1345-1357`) sad čita `data.reply` i kad
`!resp.ok`, tako da user vidi specifičnu poruku iz handler-a umjesto
generičkog "Greška servera".
