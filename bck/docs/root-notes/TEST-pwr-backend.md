# Lokalno testiranje — PWR backend za chat agent (LLM_BACKEND=pwr)

Test plan za STATUS karticu `pwrt` — kako manuelno provjeriti da migracija
sa direktnog Anthropic API-ja na PlaywrightRouter radi end-to-end prije
prebacivanja kartice u Done.

Server se diže kroz uvicorn u Python venv-u; URL je `http://localhost:8000`.
Default `LLM_BACKEND=anthropic` (produkcija nepromijenjena) — PWR se uključuje
override env var-om po pojedinačnom pokretanju.

## Pre-flight (jednom prije testiranja)

```bash
# 1. PWR Docker container je up
docker ps --format '{{.Names}}\t{{.Status}}' | grep playwright-router-router
# Očekivano: ...router-1  Up X hours (healthy)

# 2. tools_bridge.py je u image-u (T1-T6 faze; bez ovoga svi modeli
#    vraćaju plain tekst bez tool_calls — vidi TEST-failures-pwr-migration.md §4)
docker exec playwright-router-router-1 ls /app/playwright_router/server/ | grep tools_bridge.py
# Očekivano: tools_bridge.py

# 3. PWR endpoint odgovara, API key valjan
curl -sf -H "Authorization: Bearer $(grep ^API_KEY ../playwright-router/.env | cut -d= -f2)" \
  http://127.0.0.1:8765/v1/models | jq '.data | map(.id)'
# Očekivano: lista koja sadrži "claude-sonnet-4-6"
```

## Pokretanje servera za PWR test

`.env` već treba da ima `LLM_BACKEND=pwr`, `PWR_API_KEY`, `PWR_BASE_URL`
(vidi `../playwright-router/.env` za `API_KEY` vrijednost). Onda:

```bash
source .venv/bin/activate
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 7778 --log-level info
```

Alternativno (bez trajne `.env` izmjene) — override po pokretanju:

```bash
LLM_BACKEND=pwr \
PWR_API_KEY=<API_KEY iz ../playwright-router/.env> \
PWR_BASE_URL=http://127.0.0.1:8765/v1 \
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 7778 --log-level info
```

Ako je port 8000 zauzet (WSL2 + Docker proxy), koristi 7778 ili neki drugi
slobodan i zamijeni URL u curl-ovima ispod.

## Kako provjeriti backend put (PWR vs Anthropic)

`ChatResponse` (`app/main.py:171`) eksposi samo `reply`, `reply_voice`,
`channel`, `tools_used`, `escalated`, `iterations` — **`_trace` polje NIJE
u HTTP response**. Pun trace (model, tokens, latency, tool_calls) se
asinhrono persistuje u SQLite DB i čita kroz:

1. **Admin dashboard UI** — `http://localhost:5173/admin/` (treba pokrenuti
   Vite dev server, vidi `dashboard/README.md`).
2. **Dashboard API** — direktan curl sa `DASHBOARD_API_KEY` bearer-om:

   ```bash
   curl -s -H "Authorization: Bearer $(grep ^DASHBOARD_API_KEY .env | cut -d= -f2)" \
     http://localhost:7778/api/dashboard/requests | jq '.items[0]'
   ```

**Indikatori PWR put-a u request row-u** (iz DB-a, ne HTTP response-a):

| Polje | PWR vrijednost | Anthropic vrijednost |
|---|---|---|
| `adapter` | `chat:sonnet` (od `_short_model_name("claude-sonnet-4-6")`) | `chat:sonnet` ili `chat:haiku` — collision je moguć kad oba puta koriste isti model |
| `model` | `claude-sonnet-4-6` (ili šta god je `pwr_chat_model`) | `claude-sonnet-4-6` (ili `chat_model`) |
| `tokens_in` / `tokens_out` | `0` (PWR ne izlaže brojeve) — **glavni diskriminator** | `>0` |
| `latency_ms` | 60000-90000 multi-iter | 2000-5000 multi-iter |

> Napomena: `via_pwr` flag postoji u `_trace` dict-u u memoriji ali se ne
> upisuje u DB (Request DB model nema kolonu). Razlika između put-eva se
> trenutno čita iz `adapter`/`model`/`tokens` kombinacije. Vidi pwrt
> "Preostalo do Done" za potencijalni follow-up.

## Test plan

### 1. Health endpoint zelen

```bash
curl -s http://localhost:7778/healthz | jq
```

Očekivano: `status: "ok"`, RAG polja `true`. `chat_model` i `email_model` u
output-u pokazuju **Anthropic** ime — to je legacy field (settings.chat_model);
PWR-specifični modeli su `pwr_chat_model` koji se loguje samo u trace.

### 2. Smoke test — chat query trigger-uje tool_call kroz PWR

```bash
curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Trebam tastaturu do 100 KM","channel":"chat"}' | jq
```

Očekivano u HTTP response-u (~70-90s, PWR je 6-10× sporiji od Anthropic-a):

- `tools_used: ["search_products"]` — tool je pozvan, ne plain tekst.
- `iterations: 2` (ili više) — tool_call iteracija + finalize iteracija.
- `reply` sadrži ime konkretnog proizvoda + cijenu (RAG je vratio realan
  rezultat).
- `escalated: false`.

Verifikacija da je PWR put zaista korišten — provjeri zadnji request u
dashboard-u:

```bash
curl -s -H "Authorization: Bearer $(grep ^DASHBOARD_API_KEY .env | cut -d= -f2)" \
  http://localhost:7778/api/dashboard/requests \
  | jq '.items[0] | {adapter, model, tokens_in, tokens_out, latency_ms, iterations}'
```

Očekivano: `adapter: "chat:sonnet"`, `model: "claude-sonnet-4-6"`,
`tokens_in: 0`, `tokens_out: 0`, `latency_ms` između 60000-90000.
Tool_calls možeš vidjeti detaljnije preko `/api/dashboard/requests/{id}`
ili u admin UI-ju.

### 3. Default backend (LLM_BACKEND=anthropic) ostaje nepromijenjen

Zaustavi PWR uvicorn. Zakomentariši `LLM_BACKEND=pwr` red u `.env` (ili
postavi na `anthropic`). Pokreni:

```bash
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 7778
```

```bash
curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Imate li laptop do 1500 KM","channel":"chat"}' \
  | jq '{tools_used, iterations, reply: (.reply | .[0:120])}'
```

Pa provjeri dashboard request:

```bash
curl -s -H "Authorization: Bearer $(grep ^DASHBOARD_API_KEY .env | cut -d= -f2)" \
  http://localhost:7778/api/dashboard/requests | jq '.items[0] | {adapter, model, tokens_in, latency_ms}'
```

Očekivano: `adapter: "chat:sonnet"`, `model: "claude-sonnet-4-6"`,
`tokens_in > 0`, `latency_ms` između 2000-5000. Anthropic put neprostrnut.

### 4. Pytest regression (sa default backend-om)

```bash
.venv/bin/python -m pytest tests/ -m "not anthropic_api" -q
```

Očekivano: **106 passed, 10 deselected, 0 failed**. Ovo je glavna garancija
da PWR kod ne lomi Anthropic put.

### 5. Multi-iteration tool flow

```bash
curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Imate li SSD diskove 1TB do 400 KM?","channel":"chat"}' \
  | jq '{iterations, tools_used, tools_count: (.tools_used | length)}'
```

Očekivano: `iterations >= 2`, `tools_used` ima bar jedan element. Model
je radio loop: search → result → finalni reply.

Dashboard pokazuje detaljnije — request row + tool_call rows kroz:

```bash
curl -s -H "Authorization: Bearer $(grep ^DASHBOARD_API_KEY .env | cut -d= -f2)" \
  "http://localhost:7778/api/dashboard/requests/$(curl -s -H \"Authorization: Bearer $(grep ^DASHBOARD_API_KEY .env | cut -d= -f2)\" http://localhost:7778/api/dashboard/requests | jq '.items[0].id')" \
  | jq '.tool_calls'
```

`tool_calls` u DB ima isti broj kao `tools_used` u HTTP response-u.

### 6. escalate_to_human dedup (Risk #2)

Pošalji isti escalation query dva puta uzastopno:

```bash
for i in 1 2; do
  echo "=== call $i ==="
  curl -s -X POST http://localhost:7778/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message":"Trebam zvaničnu ponudu za firmu, JIB 4403711250001","channel":"chat"}' \
    | jq '{escalated, tools_used}'
done
```

Očekivano: oba poziva imaju `escalated: true` i
`tools_used: ["escalate_to_human"]`. Ako su oba u 5-min prozoru i tool je
zvao sa istim `(reason, summary)`, SMTP email se šalje samo jednom.
Provjeri SMTP outbox / `ESCALATION_EMAIL_TO` inbox — **samo 1 mail za dva
poziva**. (Ako model emituje različite `summary` tekstove između poziva,
dedup ih tretira kao različite — uobičajeno na PWR put-u jer Claude
parafraziraje.)

Tool input se vidi u dashboard-u — provjeri zadnja dva request-a kroz
`/api/dashboard/requests/{id}` da uporedi `tool_calls[].input_json`.

### 7. Voice channel collision test (Risk #1)

```bash
curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Imate li tastature do 100 KM?","channel":"voice"}' \
  | jq '{reply, reply_voice}'
```

Očekivano:

- `reply` (UI tekst) ne smije sadržavati `⟦tool_use⟧` marker.
- `reply_voice` (TTS tekst) ne smije sadržavati markdown (`**`, `](http`)
  ni `⟦tool_use⟧` marker.
- `<voice>` ili `<text>` XML tagovi NE smiju cure u `reply`.

PWR put potvrđuješ kroz dashboard request row (`adapter: "chat:sonnet"`,
`tokens_in: 0`).

Ponovi sa još 4-5 voice upita (laptop, garancija, pozdrav, miš) da pokriješ
varijetet. PWR je u testiranju emitovao 0/5 leak-ova.

### 8. Email channel

```bash
curl -s -X POST http://localhost:7778/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Pozdrav, zanima me imate li gaming miševe u ponudi.","channel":"email"}' \
  | jq -r '.reply' | head -5
```

Očekivano: `reply` počinje sa "Poštovani" (email preamble trim radi i kroz
PWR put), bez `<text>`/`<voice>` tagova. PWR put potvrđuješ kroz dashboard
request row.

### 9. Eval skripte preko PWR

Category accuracy (samo iteracija 1, brzo — ~5min):

```bash
LLM_BACKEND=pwr PWR_API_KEY=... PWR_BASE_URL=http://127.0.0.1:8765/v1 \
  .venv/bin/python -c '
import json, openai, time
from pathlib import Path
from app.config import settings
from app.system_prompts import system_prompt
from app.tools import ALL_TOOLS_OPENAI_SHAPE
c = openai.OpenAI(base_url=settings.pwr_base_url, api_key=settings.pwr_api_key)
cases = json.loads(Path("evals/category_eval.json").read_text())
ok = 0
for case in cases:
    r = c.chat.completions.create(model=settings.pwr_chat_model,
        messages=[{"role":"system","content":system_prompt("chat")},
                  {"role":"user","content":case["query"]}],
        tools=ALL_TOOLS_OPENAI_SHAPE, max_tokens=500)
    tcs = r.choices[0].message.tool_calls or []
    got = json.loads(tcs[0].function.arguments).get("category_id") if tcs else None
    ok += (got == case["expected_category_id"])
print(f"{ok}/{len(cases)} = {ok/len(cases):.1%}")'
```

DoD threshold: ≥85% (zadnja mjerenja 40/41 = 97.6%).

Full HTTP eval (sve 20 pitanja, ~10min sa PWR):

```bash
# .venv/bin/python evals/run.py ima hardcoded TIMEOUT_S=60 — premalo za PWR.
# Ad-hoc varijanta sa 300s timeout-om je u session log-u, vrijedi recyclovati.
```

DoD threshold: ≥80% (zadnja mjerenja 19/20 = 95%).

### 10. Frontend smoke (browser)

Otvori `http://localhost:7778/` u browser-u, hard-reload (Ctrl+Shift+R),
otvori DevTools → Network tab, klikni chat bubble i pošalji upit "Trebam
laptop". Provjeri:

- Network: jedan POST na `/api/chat`, response status 200, trajanje 60-90s
  (PWR latency — strpljivo).
- Reply renderuje proizvode sa slikama i linkovima isto kao Anthropic put.
- Console čista (bez `⟦tool_use⟧` marker leak-a, bez raw XML tagova).

## Poznati pad-ovi prije nego što pwrt ide u Done

Vidi [`TEST-failures-pwr-migration.md`](TEST-failures-pwr-migration.md):

- `category_eval` #39 (typo "telfon" + 1. lice množine) — LOW prio.
- HTTP eval #16 (voice markdown leak u `<text>` bloku) — LOW prio,
  pre-postojeći prompt issue.
- `torch.nn.Module.to_empty` u `rag.preload_model` nakon ~25 requesta —
  MID prio, pogađa i Anthropic put. Workaround: server restart.

## Rollback na Anthropic

Bez izmjene koda — `LLM_BACKEND=anthropic` (ili izostanak env var-a) vraća
default. Working tree PWR koda može stajati zauvijek bez efekta na
produkciju jer je dispečer u `app/agent.py:run_agent` strogo branching na
`settings.llm_backend`.
