# Logging dashboard

> Zasebna React + Vite + TS aplikacija u `dashboard/` direktorijumu.
> Prikazuje **fine-grained AI workflow** umjesto black-box logova.

## Šta vidi korisnik

Otvori `http://localhost:5173/admin/` (dev) ili `https://<domain>/admin/` (prod), unesi `DASHBOARD_API_KEY` u Settings, save.

| Stranica | Šta prikazuje |
|---|---|
| **Sessions** (default) | **Thread view** — jedan red = jedan razgovor klijent+AI. Vidi [`sessions.md`](./sessions.md) |
| **SessionDetail** | Turn-by-turn cijela komunikacija pitanje→odgovor sa tool calls između |
| **Live** | Message-level polling 5s, fresh-row highlight, klik na red → RequestDetail |
| **History** | Paginated message-level, filteri po channel/status |
| **Compare** | Paste upit → fan-out kroz haiku + sonnet paralelno → side-by-side rezultati sa latency, tokens, cost, tool call summary |
| **RequestDetail** | Top metrike (status, iteracije, tokens, latency, cost), prompt, error block, **timeline svakog tool call-a** (expand/collapse: input JSON, output text, latency badge), final response |
| **Stats** | Top-line cards (total req, tokens, cost) + by-adapter (channel × model) tabela |
| **Settings** | Input za `DASHBOARD_API_KEY`, env diagnostika |

## Šta diferencira (vs konkurencija)

Tool call timeline u **RequestDetail** je glavni pokazatelj — za svaki request korisnik vidi:

```
iter#1 search_products({"query":"gaming miš", "category_id":"277"})  → 3500ms
       output: 5 produkti vraćena, json...
iter#2 escalate_to_human({"reason":"ostalo"})                          → 2ms
       output: Eskalacija inicirana...
```

Bez ovoga AI je black box. Sa ovim vidi se tačno **šta** je AI uradio, **kako**, **koliko je trajalo**, i **koliko je koštalo**. To je input za prompt iteracije i model eval.

## Backend

Sve pod `/api/dashboard/` sa Bearer auth (header `Authorization: Bearer <DASHBOARD_API_KEY>`).

| Endpoint | Šta vraća |
|---|---|
| `GET /requests?adapter=&channel=&status=&page=` | Paginated lista |
| `GET /requests/:id` | Detail sa `tool_calls[]` |
| `GET /stats` | Top-line + by-adapter breakdown |
| `GET /errors` | Failed requests |
| `POST /compare` | `{message, channel, models[]}` → fan-out kroz `asyncio.gather`, vraća listu sa `compare_group_id` |

Bez tokena → 401. Pogrešan token → 401.

### Compare endpoint primjer

```bash
curl -sX POST https://<domain>/api/dashboard/compare \
  -H "Authorization: Bearer $DASHBOARD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"imate li tastaturu","channel":"chat","models":["haiku","sonnet"]}'
```

Vraća:
```json
{
  "compare_group_id": "21d33932...",
  "results": [
    {"model_key":"haiku","status":"ok","latency_ms":6470,"tokens_in":9467,
     "tokens_out":215,"cost_usd":0.0105,"reply":"...","tool_calls":[...]},
    {"model_key":"sonnet","status":"ok","latency_ms":17074,"tokens_in":13834,
     "tokens_out":257,"cost_usd":0.0454,"reply":"...","tool_calls":[...]}
  ]
}
```

Oba se loguju u DB sa istim `compare_group_id` — vidiš grupisano u Live/History.

## Storage

SQLite + SQLAlchemy async, `var/bitlab.db`. Tabele:

```
requests:
  id, adapter ("<channel>:<model>"), channel, model, prompt, response,
  tokens_in, tokens_out, latency_ms, iterations, status, error,
  compare_group_id, created_at

tool_calls:
  id, request_id (FK), iteration, tool_name, input_json,
  output_text (truncated 4KB), latency_ms, created_at
```

Tracker u `agent.py`:
- `run_agent()` interfejs ostaje (vraća isti dict + dodatno `_trace`)
- Wrapper oko `dispatch()` mjeri latency po tool call-u
- Persist je **fire-and-forget** kroz `asyncio.create_task(_persist_trace(...))` u `main.py` — chat ne čeka DB pisanje
- Greške u DB pisanju se loguju ali ne ruše chat

## Frontend struktura

```
dashboard/src/
├── App.tsx                  6 ruta (Live, History, Compare, RequestDetail, Stats, Settings)
├── components/
│   ├── Layout.tsx           sidebar 232px (BitLab orange accent) + main scroll
│   └── atoms.tsx            Tag, Btn, Metric, StatusBadge, TopBar, SectionLabel
├── pages/                   6 stranica (vidi tabela gore)
├── api.ts                   axios client + Bearer interceptor (localStorage)
├── tokens.ts                dark theme + per-channel/model boje
└── main.tsx                 BrowserRouter + TanStack Query client
```

Build: `cd dashboard && pnpm install && pnpm build` → `dashboard/dist/` (~336KB JS / 106KB gzipped).

Production: nginx servira `dist/` pod `/admin/` location, API ide kroz proxy na `/api/dashboard/`.

## Auth

`DASHBOARD_API_KEY` u `.env`. Generiši:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Dashboard čuva u `localStorage.bitlab.dashboardKey`. Settings stranica ima input. Promjena → save → reload (force-fresh sve TanStack Query keys).

## Cost izračun

`COST_PER_M` u `app/server/dashboard.py` (USD per 1M tokena, hardkodirano):
- `claude-haiku-4-5-20251001`: $1 in / $5 out
- `claude-sonnet-4-6`: $3 in / $15 out

Po request: `(tokens_in × in_rate + tokens_out × out_rate) / 1_000_000`

## Kako iskoristiti za prompt iteraciju

1. Otvori Live → vidi šta korisnici realno pitaju
2. Klik na request gdje AI nije reagovao kako treba → RequestDetail
3. Vidi tool calls timeline — gdje je AI pogriješio (npr. nije pozvao search, ili poslao pogrešan category_id)
4. Idi na Compare, paste isti upit, isprobaj sa drugim modelom ili promijeni system prompt
5. Stats prati cost trend, prepoznaj jeftiniji model za isti use case
