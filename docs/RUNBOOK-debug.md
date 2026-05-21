# RUNBOOK — local debug

Klikni-i-kopiraj referenca za sve što treba kad debug-uješ ponašanje sistema lokalno. Pokriva: pokretanje servera, dashboard frontend, sibling Playwright Router, eval skripte za parent kategorije, šta tačno gledati u dashboard-u, i kratak primer agent loop-a (turns vs iteracije).

## 1. Pokreni servere

### Lokalni URL-ovi koje otvaraš u browser-u

- **Dashboard (Vite dev):** `http://localhost:5173/admin/`
- **Backend (FastAPI):** `http://localhost:7778` (healthz, widget, API)
- **Widget demo:** `http://localhost:7778/public/widget.html`
- **Voice panel:** `http://localhost:7778/public/voice.html`

Prije prvog pokretanja dashboard-a: u `dashboard/vite.config.ts` izmijeni proxy target sa `http://localhost:8000` na `http://localhost:7778` da bi vite dev pogađao tvoj lokalni backend. Bez tog edit-a, `/api/*` pozivi iz dashboard-a vraćaju connection refused.

```ts
// dashboard/vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:7778',  // bilo '8000'
  },
},
```

### 1.1 FastAPI backend (BitLab AI Asistent)

```bash
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent && \
  source .venv/bin/activate && \
  uvicorn app.main:app --reload --port 7778
```

Port `7778` je konvencija za lokalni dev (eval skripte podrazumijevaju njega). Prod radi na `8000`. Ako koristiš dashboard preko vite proxy-ja, vidi sekciju 1.2 — proxy upire na port `8000`, pa dashboard treba ili pokrenuti backend na `8000` ili izmijeniti proxy.

Healthcheck:

```bash
curl -sS http://127.0.0.1:7778/healthz | python3 -m json.tool
```

### 1.2 Dashboard frontend (Vite dev)

```bash
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent/dashboard && pnpm dev
```

Vite se diže na `http://localhost:5173/admin/`. Proxy target u `vite.config.ts` mora pokazivati na backend port — vidi "Lokalni URL-ovi" sekciju iznad za eksplicitan edit (8000 → 7778).

Build (za production simulaciju):

```bash
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent/dashboard && pnpm build
```

Za live prod dashboard: `https://aiasistent.bitlab.rs/admin/` (treba Bearer `DASHBOARD_API_KEY` u localStorage ili browser fetch headerima).

### 1.3 Playwright Router (sibling repo, ako treba "Chrome login" za pwr backend)

```bash
cd /mnt/c/Users/Kule/Projects/playwright-router && pnpm dev
```

Default API port `:8765`. Dashboard: `/admin/` ili odgovarajući mount (vidi `playwright-router/README.md` — env tabela na vrhu).

Live deploys:

| Env     | API                                                  | noVNC tab (login flow)                                            |
|---------|------------------------------------------------------|-------------------------------------------------------------------|
| Staging | `https://staging.compliance.bitlab.rs/playwright-router/` | `…/playwright-router/vnc/vnc.html?path=playwright-router/vnc/websockify` |
| Prod    | `https://compliance.bitlab.rs/playwright-router/`         | isto, bez `staging.` prefiks                                       |

Health:

```bash
curl -sS https://compliance.bitlab.rs/playwright-router/health
```

## 2. Eval skripte — šta koristiti kad

| Skripta                                | Bez servera | Sa /api/chat | Šta vidiš                                              |
|----------------------------------------|-------------|--------------|--------------------------------------------------------|
| `evals/visualize_parent_expansion.py`  | ✓           | —            | TEORETSKA before/after slika (hard filter)             |
| `evals/visualize_parent_runtime.py`    | —           | ✓            | REALNO ponašanje — koji cat Claude šalje, koliko vraća |
| `evals/test_e2e_visual.py`             | —           | ✓            | Brz CLI test sa fiksiranim QUESTION_SET (v1/v2/hard/inj) |
| `evals/run_categories_html.py`         | —           | ✗ (CLI klasifikacija) | Samo routing — da li Claude bira tačan `category_id`  |
| `evals/run_e2e_html.py`                | —           | ✓            | Pun e2e za 42 upita iz `category_eval.json`            |

### 2.1 Parent expansion (teoretski)

```bash
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent && python evals/visualize_parent_expansion.py
```

Output: `evals/runs/parent-expansion-{TS}.html`. Inspektuje `app/rag.py` na disku — verdict banner zavisi od trenutne grane:
- Zeleno PASS = fix u kodu (current = subtree).
- Crveno FAIL = fix nije u kodu (current = direct, mala brojka).

### 2.2 Parent runtime (realno)

```bash
# Smoke test (3 upita)
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent && python evals/visualize_parent_runtime.py --limit 3
```

```bash
# Pun baseline (15 parent upita), označeno za regression compare
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent && python evals/visualize_parent_runtime.py --label v1-baseline
```

```bash
# Protiv staging-a
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent && python evals/visualize_parent_runtime.py --url https://staging.aiasistent.bitlab.rs --label v1-staging
```

Output: `evals/runs/parent-runtime-{label}-{TS}.html`.

### 2.3 E2E test set (42 upita)

```bash
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent && python evals/run_e2e_html.py
```

Trajanje ~20 min. Output: `docs/category-analysis/e2e-run-latest.html`.

## 3. Šta gledati u dashboard-u

Dashboard ima 4 glavna taba kroz `/api/dashboard/*` endpoint-e. Bearer auth obavezan — token iz `.env` `DASHBOARD_API_KEY`.

| Tab          | API endpoint                       | Šta pokazuje                                                    |
|--------------|------------------------------------|-----------------------------------------------------------------|
| Requests     | `GET /api/dashboard/requests`      | Pojedinačni `/api/chat` pozivi: prompt, reply, latency, escalated |
| Request detail | `GET /api/dashboard/requests/{id}` | Pun `_trace` — svaki tool_call sa input + output                |
| Sessions     | `GET /api/dashboard/sessions`      | Grupisano po `session_id` — full razgovor multiple turn-ova     |
| Session detail | `GET /api/dashboard/sessions/{sid}` | Linija po liniji turn + sve iteracije                         |
| Stats        | `GET /api/dashboard/stats`         | Aggregates — escalation rate, average iterations, top tools     |
| Errors       | `GET /api/dashboard/errors`        | Filter za failed runs / Anthropic API errors                    |
| Overview     | `GET /api/dashboard/overview`      | Quick KPIs (zadnjih N requesta + trend)                         |
| Compare      | `POST /api/dashboard/compare`      | A/B dva trace-a — koje tool argumente je svaki proslijedio      |

### 3.1 Ključne kolone za debug

Kad otvoriš Request detail:

- **prompt** — šta je user poslao (`req.message`).
- **tool_calls[]** — niz svih tool poziva u tom turn-u:
  - `iteration` — koja iteracija unutar turn-a (1 = prvi tool poziv, 2 = drugi, …).
  - `tool_name` — `search_products`, `get_faq`, `check_availability`, `escalate_to_human`.
  - `input_json` — argumenti (uključujući `category_id`, `brand_id`, `top_k`, `query`).
  - `output_text` — šta je tool vratio (LLM ovo vidi pri sljedećoj iteraciji).
  - `latency_ms` — koliko traje sam tool poziv.
- **reply** — finalni Claude tekst korisniku.
- **iterations** — ukupno koliko iteracija prošlo (vidi sekciju 4).
- **escalated** — true ako je pozvan `escalate_to_human` (auto email u prodaja@bitlab.rs).
- **model + effort + via_pwr** — koji LLM backend.

**Tipičan debug flow:** otvori Requests tab, pronađi sumnjivi request, klikni za detail, pogledaj `tool_calls` — vidiš koju je kategoriju Claude izabrao i šta mu je tool vratio.

## 4. Agent loop primer — turns vs iteracije

**Turn** = jedan razmijenjen "krug": user poruka + Claude odgovor. Multi-turn razgovor = istorija u `req.history`.

**Iteracija** = unutar JEDNOG turn-a, Claude može u petlji pozivati tool-ove dok ne odluči da završi. Tipično:

1. **iteration 1** — Claude vidi user prompt, odluči `search_products(query="laptop do 1500 KM", category_id=98)` → dobije listu proizvoda.
2. **iteration 2** — Claude vidi rezultat, možda zaključi da treba još info i pozove `check_availability(sifra="L123")` → dobije stanje.
3. **iteration 3** — Claude ima sve što treba, generiše final reply, petlja se prekida.

Default max iteracija je `settings.max_tool_iterations` (10) — guard da Claude ne zaglavi u beskonačnoj petlji. Većina realnih zahtjeva završi za 1–3 iteracije.

**Ne mješati:** turn (između user-a i agent-a) vs iteration (unutar jednog turn-a, samo agent ↔ tool).

## 5. Quick debug recipes

### "Claude ne vraća očekivane proizvode za upit X"

1. Pokreni runtime visualizer: `python evals/visualize_parent_runtime.py --limit 3` (sa custom query setom ako treba).
2. Otvori HTML, klikni red za upit X.
3. Pogledaj `search_products tool calls` — koji `category_id` je poslat?
4. Pogledaj `Returned products + map-back` — koji su proizvodi vraćeni i u kojem cat-u žive?
5. Ako routing pogrešan → problem je u `tool_description` (klasifikacija) ili `system_prompts.py`.
6. Ako routing OK ali rezultati slabi → problem je u `app/rag.py` hibridnoj pretrazi.

### "Servis radi, ali rezultat se promijenio nakon update-a"

1. Pokreni baseline runtime sa novim kodom: `python evals/visualize_parent_runtime.py --label v2-after-change`.
2. Otvori `parent-runtime-v1-baseline-*.html` (od prije) i `parent-runtime-v2-after-change-*.html` side-by-side.
3. Uporedi PASS/WARN/FAIL counts u verdict banneru.
4. Per-query: vidi da li je routing badge promijenio (NULL → DESCENDANT je obično dobro, DESCENDANT → EXACT_PARENT je opasno).

### "Trebam vidjeti tačno šta je Claude poslao za jedan razgovor"

1. U Vite dashboard-u, otvori Requests ili Sessions tab.
2. Pronađi konkretan request po prompt-u.
3. Klikni → Request detail.
4. Skroluj do `tool_calls` sekcije — vidiš svaku iteraciju, input JSON, output, latency.

### "Server radi ali nešto je sporo / hangs"

```bash
# Šta sluša na portu 7778
sudo ss -tlnp | grep :7778
```

```bash
# Procesi koji troše najviše memorije (lokalno na WSL)
ps aux --sort=-rss | head -10
```

```bash
# uvicorn log — sa --reload prikazuje sve u terminalu gdje je pokrenut
# Ako nije, journal/log file zavisi od konfiguracije
```

### "Test all-products name → cat lookup je promašio"

Runtime visualizer fallback je exact + lowercase match. Ako Claude reproduce-uje name sa razmacima/zarezima drugačije od `all-products.json`, mapping ne radi.

Rješenje: refresh `data/all-products.json` (phpMyAdmin re-export) ili dodaj fuzzy match u `match_product_cat` u `evals/visualize_parent_runtime.py`.

## 6. Linkovi na ostale runbooks

- **Server services** (gdje šta vrti na VPS-u, start/stop/logs): `deploy/RUNBOOK-services.md`
- **Prod first-time setup**: `deploy/RUNBOOK-prod.md`
- **Manual prod setup (debug ako `setup-domain` pukne)**: `deploy/MANUAL-setup-domain.md`
- **Eval skripte README**: docstringovi u svakom `evals/*.py` fajlu (top of file)
- **Parent fix test plan**: `TEST_category-parent_id_fix.md`
