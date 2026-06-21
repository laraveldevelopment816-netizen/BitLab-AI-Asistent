# BitLab AI Asistent — Plan za produkciju (Sesija 8)

> **Cilj:** Chat + Voice + Email + Logging dashboard u stanju "spremno za prezentaciju i produkciju" do **2026-05-04 16:00**.
> **Grana:** `production-prep`. Merge na `main` kad svi DoD prođu.
> **Vremenski budžet:** ~6h. Buffer ~25 min.
> **Princip modela:** Opus 4.7 = arhitekturne odluke i precizni jednoiteracijski pass-ovi. Sonnet 4.6 = polish, deploy, smoke.

---

## 0. Tech stack — final

| Sloj | Tehnologija | Razlog |
|---|---|---|
| Backend | **FastAPI / Python** (postojeći) | nema promjene — **NIKAD Node u runtime-u** |
| Storage | **SQLite + SQLAlchemy async** (`aiosqlite`) | port iz `playwright-router/storage/` |
| Dashboard | **React 19 + Vite 8 + TS + Tailwind 4** | port iz `playwright-router/dashboard/` |
| Dashboard runtime | **statički `dist/` servira nginx** | Node je prisutan samo na build mašini, nikad na produkcionom serveru u runtime-u |
| Live update | **HTTP polling 5s** kroz TanStack Query | dovoljno za demo; bez WS-a |
| Ostalo | postojeći (`anthropic`, `sentence-transformers`, `httpx`, `edge-tts`, `faster-whisper`) | nepromijenjeno |

> **Eksplicitno o Node-u:** koristi se **isključivo kao build tool** (`pnpm install`, `pnpm build`) da generiše statičke HTML+JS+CSS fajlove u `dashboard/dist/`. Na VPS-u se servira samo taj `dist/` kroz nginx. Backend = Python/FastAPI, **bez Express-a, bez `server.js`**. Stari `PLAN.md` (april) opisuje napuštenu Node.js verziju i označen je `DEPRECATED`.

---

## 1. Šta zaista mora ući u 16h prezentacije

| # | Stavka | Prioritet |
|---|---|---|
| 1 | **Kategorije — AI klasifikacija namjere** | **P0** |
| 2 | **Logging dashboard (React + Vite, port iz playwright-routera)** | **P0 — pomjereno ispred voice-a** |
| 3 | UX preraspodjela voice widget-a | P0 vizuelno |
| 4 | Deploy na VPS | P0 za produkciju |
| 5 | Smoke test, eval, README, PR | P0 |

**Stop-loss u 14:30:** ako dashboard frontend ili voice UX kasne, mergujemo P0 + deploy. Frontend WIP ostaje na grani.

---

## 2. Polazni materijal — `playwright-router` reuse

`/mnt/c/Users/Kule/Projects/playwright-router/` je glavna ušteda — sve nam treba kopirati uz minimalnu adaptaciju.

### Backend (kopiraj-i-prilagodi)
- `playwright_router/storage/models.py` → `Request` SQLAlchemy model. **Adaptacija:** `adapter` polje koristimo kao `"<channel>:<model>"` → `chat:haiku`, `chat:sonnet`, `voice:haiku`, `voice:sonnet`, `email:sonnet`, `compare:haiku`, `compare:sonnet`, `stt:groq`, `stt:azure`, `tts:azure`, `tts:edge`.
- `playwright_router/storage/repo.py` → `insert_request()` helper.
- `playwright_router/storage/tracker.py` → ideja za tracker; naš je nešto drugačiji jer zovemo agent loop, ne single send.
- `playwright_router/server/dashboard.py` → router pod `/api/dashboard/` (`/requests`, `/:id`, `/stats`, `/errors`) — radi as-is uz import path fix.
- **Nova `tool_calls` tabela** (router je nema): fine-grained log po koraku agent loop-a — naš diferencijator za prezentaciju.

### Frontend (kopiraj-i-prilagodi)
- Cijeli `playwright-router/dashboard/` se kopira u naš `dashboard/` folder. Skida se `node_modules/`, `dist/`, `pnpm-lock.yaml` (regeneriše).
- `package.json` ostaje (React 19, Vite 8, Tailwind 4, react-router 7, TanStack Query, axios).
- `App.tsx`, `components/Layout.tsx`, `components/atoms.tsx` ostaju. `tokens.ts` ostaje (dark theme).
- `api.ts` se proširuje sa `tool_calls`, `channel`, `compare` tipovima.
- **Držimo 6 stranica:** `Live`, `History`, `Compare`, `RequestDetail`, `Stats`, `Settings`.
- **Brišemo iz rute:** `Adapters`, `Errors`, `Health`, `Roadmap`, `Templates`, `Compose` (van skopa za prezentaciju).
- Brand tweak: sidebar wordmark → "bitlab-ai · v0.8", dodaj BitLab orange `#fb6d3b` kao secondary accent.

### Šta NE uzimamo
- `adapters/`, `core/router.py`, `core/health_monitor.py` iz backenda — nemamo browser adaptere.

---

## 3. Pregled sesija

| # | Naziv | Model · Effort | Trajanje | Output |
|---|---|---|---|---|
| 0 | Branch + plan + reuse audit | Sonnet · low | 15m | grana, ovaj fajl |
| 1 | **Kategorije — intent classification** | **Opus · high** | 75m | `data/categories.json`, `search_products + category_id`, eval ≥80% |
| 2 | **Dashboard backend + tracker** | **Opus · high** | 60m | SQLAlchemy async, `tool_calls`, JSON API, agent loop logging |
| 3 | **Dashboard frontend (port iz playwright-routera)** | **Opus · high** | 75m | `dashboard/` Vite app, 6 stranica, brand tweak, build prolazi |
| 4 | Voice widget UX redesign | Sonnet · medium | 50m | header 25% / body 75%, perzistencija rezultata |
| 5 | Deploy na VPS | Sonnet · medium | 60m | systemd + nginx, dashboard `dist/` served, smoke |
| 6 | Smoke + eval + PR | Sonnet · low | 30m | DoD ✅, PR opis |

Ukupno: 5h45m.

> **Zašto Opus na 1, 2, 3:** Sesija 1 je arhitekturna odluka. Sesije 2 i 3 imaju jasan polazni materijal u `playwright-router`-u — Opus radi precizan port + adaptaciju u jednom passu. Sonnet bi iterirao 3–5× na verzionim/import quirk-ovima (async SQLAlchemy, Vite 8 + React 19 + TS 6 + Tailwind 4 specifičnosti). Manje tokena ukupno.

---

## 4. Sesija 1 — Kategorije (Opus 4.7, high, 75m)

### Zašto Opus high
Arhitekturna odluka koju je skupo ispraviti: gdje živi mapiranje (JSON vs DB), klasifikacija kao parametar postojećeg `search_products` toola **vs** zaseban `classify_intent` tool, kako se enum drži pod kontrolom.

### Šta se radi
1. **`scripts/build_categories.py`** — čita `data/products.meta.json`, broji proizvode po `categories_id`, uzima top 30 (pokrivaju 81.5% kataloga; ostatak u `_other`). Per-kategoriju izračuna **human-readable label** iz najčešćih leading tokena imena.
   Output `data/categories.json`:
   ```json
   {
     "394": {"label": "SSD diskovi", "examples": ["SSD 240GB Patriot…"], "count": 1274},
     "277": {"label": "Tastature i miševi", ...}
   }
   ```
2. **`tools.py`** — dodaj **opcioni** `category_id` parametar u `search_products` schema. Bez argumenta ponašanje ostaje kao danas.
3. **`rag.py`** — u `search()`: ako je `category_id` zadat, hard filter + hibrid scoring unutar kategorije.
4. **`system_prompts.py`** — u `search_products` tool description ubaci listu `id → label` (auto-load iz `categories.json` na startu). Pravilo: "ako je upit kategorijski, prvo izaberi `category_id`; ako je konkretan brand+model, ne moraš".
5. **`evals/category_eval.json`** — 25 realnih upita + očekivani `category_id`. `evals/run_categories.py` mjeri top-1 hit rate.

### DoD Sesije 1
- [ ] `data/categories.json` ≥30 kategorija, deterministički regenerišuće
- [ ] `search_products` prihvata `category_id` (unit test)
- [ ] Eval ≥ 80% top-1 category accuracy
- [ ] Bez regresija na postojeći `evals/run.py`

---

## 5. Sesija 2 — Dashboard backend + tracker (Opus 4.7, high, 60m)

### Šta se radi
1. **Schema:**
   - `requests` tabela (port iz playwright-routera) — `adapter` = `"<channel>:<model>"`.
   - **Nova `tool_calls` tabela:**
     ```python
     class ToolCall:
         id: int (PK, autoinc)
         request_id: int (FK → requests.id, indexed)
         iteration: int          # 1..N
         tool_name: str          # search_products / get_faq / check_availability / escalate_to_human
         input_json: str
         output_text: str        # skraćen na 4KB
         latency_ms: int
         created_at: datetime
     ```
   - Razlog: prezentacijski moćno — RequestDetail pokazuje "korak 1: search_products(query='ssd 1tb', category_id='394') → 5 rezultata u 12ms".

2. **Tracker u `agent.py`:**
   - `run_agent()` interfejs ostaje. Wrapper oko `dispatch()` mjeri latency po tool call-u, snima `ToolCall`.
   - Na kraju `run_agent` snima `Request` (prompt, response, total latency, total tokens iz `response.usage`).
   - Failure path: `status='error'`, `error` polje popunjeno, ostatak NULL.

3. **Moduli:**
   - `app/db.py` — port `playwright-router/storage/db.py`, default `var/bitlab.db`.
   - `app/storage/models.py` — `Request` + `ToolCall`.
   - `app/storage/repo.py` — `insert_request()`, `insert_tool_call()`, `get_request_with_tool_calls(id)`.
   - `app/server/dashboard.py` — JSON API router pod `/api/dashboard/`:
     - `GET /requests?adapter=&status=&channel=&page=`
     - `GET /requests/:id` (sa `tool_calls[]`)
     - `GET /stats`
     - `GET /errors`
     - `POST /compare` body `{message, channel, models: ["haiku","sonnet"], history?}` → fan-out kroz `asyncio.gather`, vraća listu odgovora; loguje sve sa zajedničkim `compare_group_id`.
   - `scripts/init_db.py` — kreira tabele idempotentno.

4. **Auth:** bearer iz `.env` `DASHBOARD_API_KEY`. Bez ključa → 401.

5. **Registracija:** u `app/main.py` dodaj `app.include_router(dashboard_router)`.

### DoD Sesije 2
- [ ] `python scripts/init_db.py` → `var/bitlab.db` ima `requests` + `tool_calls`
- [ ] Jedan `POST /api/chat` upiše red u `requests` + N redova u `tool_calls`
- [ ] `/api/dashboard/requests/:id` vraća detail sa `tool_calls`
- [ ] `/api/dashboard/compare` vraća validne odgovore za oba modela u <8s, oba zalogovana
- [ ] Bez auth tokena → 401
- [ ] Bez regresija u `pytest`

---

## 6. Sesija 3 — Dashboard frontend (Opus 4.7, high, 75m)

### Zašto Opus high
Skoro sve postoji u `playwright-router/dashboard/`. Posao je port + 6 stranica + adaptacija API tipova na naš `tool_calls` schema + brand tweak. Vite 8 + React 19 + TS 6 + Tailwind 4 ima dosta verzijskih specifičnosti gdje Sonnet pravi tipsku pogrešku za pogreškom — Opus to riješava odjednom.

### Šta se radi
1. **Skeleton:** `cp -r playwright-router/dashboard/ <our-repo>/dashboard/`. Ukloni `node_modules/`, `dist/`, `pnpm-lock.yaml`. Pokreni `pnpm install`.

2. **Adaptacija `App.tsx`:**
   - Drži rute za: `/live`, `/history`, `/compare`, `/stats`, `/settings`, `/requests/:id`.
   - Uklanja: `/adapters`, `/templates`, `/cost`, `/roadmap`.
   - Default redirect `/` → `/live`.

3. **Branding (`Layout.tsx`, `tokens.ts`):**
   - Wordmark "bitlab-ai · v0.8".
   - Dodaj `bitlab: '#fb6d3b'` u tokens.
   - SVG mark zamijeni jednostavnim BitLab logo-om (ili tekst).
   - Sidebar nav update na 6 stavki sa `hint`-ovima.

4. **`api.ts` adaptacija:**
   - `baseURL` iz env: `import.meta.env.VITE_API_BASE` (default `http://localhost:8000`).
   - Dodaj `tool_calls: ToolCall[]` na `RequestDetail`.
   - Dodaj `channel: 'chat'|'voice'|'email'|'compare'` na `RequestRow`.
   - Dodaj `api.compare(message, channel, models)` POST.
   - Axios interceptor za `Authorization: Bearer ${localStorage.dashboardKey}`.

5. **6 stranica:**
   - **Live** (`Live.tsx`) — TanStack Query polling sa `refetchInterval: 5000`. Tabela 50 zadnjih, fresh-row highlight CSS animation 1.5s.
   - **History** (`History.tsx`) — paginated, filter po channel/model/status/search.
   - **Compare** (`Compare.tsx`) — port postojeće Compare.tsx; adapter pickers → `["haiku","sonnet"]`; gađa `/api/dashboard/compare` umjesto `/v1/chat/completions`.
   - **RequestDetail** (`RequestDetail.tsx`) — full strana sa: prompt, final response, **timeline tool_calls-ova** (najvažnije za demo: za svaki call expand/collapse `tool_name`, formatted `input_json`, truncated `output_text`, latency badge).
   - **Stats** (`Stats.tsx`) — top-line cards (total req, tokens, cost) + by-channel × by-model tabela.
   - **Settings** (`Settings.tsx`) — input za API ključ (čuva u localStorage), env diagnostika.

6. **Build:** `pnpm build` → `dashboard/dist/`. U Sesiji 5 nginx servira.

### Granica skopa
- Bez WS-a (TanStack Query polling 5s je dovoljan).
- Bez per-token streaminga.
- Mobilni nije optimizovan.

### DoD Sesije 3
- [ ] `pnpm dev` u `dashboard/` pokreće app na :5173
- [ ] Live stranica vidi nove request-e koje napravim curl-om
- [ ] RequestDetail prikazuje **bar 3 tool call-a** za upit "imate li ssd 1tb?"
- [ ] Compare gađa oba modela paralelno, prikazuje rezultate side-by-side
- [ ] Stats prikazuje by-channel breakdown
- [ ] `pnpm build` prolazi bez TypeScript greška

---

## 7. Sesija 4 — Voice widget UX redesign (Sonnet 4.6, medium, 50m)

### Šta se radi
Promjene su isključivo u `public/widget.js` u voice mode-u:

1. **Header (~25% visine):** mic button smanjen, state pill (idle/listening/speaking), tps/timer indicator.
2. **Body (~75%):** product card lista (kao u chat mode-u); auto-scroll na nove rezultate.
3. **Footer:** stop / prebaci-na-chat dugme.
4. **Persistencija** rezultata pri voice ↔ chat swap-u.
5. **Mobilni breakpoint** `<420px`: header 20%, body 80%, mic ≥44×44px touch target.

### DoD Sesije 4
- [ ] "Imate li SSD?" u voice mode-u → glas + lista vidljiva
- [ ] Mobilni 360px ne pukne (Chrome DevTools)
- [ ] Bez regresija u chat mode-u

---

## 8. Sesija 5 — Deploy artefakti (Sonnet/Opus medium, 50m)

> **Promjena pristupa:** umjesto da deploy radimo iz lokalne grane preko SSH-a,
> Claude Code se instalira **na samom serveru** kao zasebna sesija (sa novom
> subscripcijom za paralelni rad). Ova sesija samo priprema deploy artefakte;
> stvarni install i konfiguracija (nginx, systemd, symlinks) izvršava
> server-side Claude direktnim pristupom shell-u.
>
> **Razlog:** projekat će tokom razvoja imati još mikro-servise (n8n migracija,
> dodatni adapteri, monitoring), pa svaki put 5+ podešavanja kroz pipe nazad
> kroz lokalni env je trošenje vremena. Server-side Claude radi sve to
> jednim passom.

### ⚠️ TAČKA 0 — Server već hostuje 4 aplikacije

Server koji koristimo već ima **4 druge aplikacije, svaka na svom domenu**, sa
postojećim konvencijama (layout direktorijuma, service user-i, port alokacija,
nginx struktura, SSL setup). **Naš deploy se prilagođava njihovim pravilima,
NE obrnuto.**

**Server-side Claude (kasnije) MORA prvo:**
1. Sačekati da Ivan objasni server konvencije:
   - Gdje žive servisi (`/opt/`, `/srv/`, `/var/www/`, drugo)
   - Service user (`www-data`, jedan zajednički, per-app)
   - Rezervisani portovi i konfliktni portovi
   - nginx layout: `sites-available/` ili `conf.d/`
   - SSL: per-domen vs wildcard
   - Logging konvencija
   - venv per-app vs shared
   - Postojeća backup/rollback strategija
2. Ažurirati naše artefakte (`scripts/deploy.sh` varijable, `deploy/bitlab-ai.service` putanje, `deploy/nginx-site.conf` paths) **PRIJE** izvršenja
3. Tek onda pokrenuti install flow

**Default-i koji vjerovatno trebaju promjenu:** `PROJECT_DIR=/opt/bitlab-ai`,
`SERVICE_USER=bitlab`, port `8000`, dashboard u `/var/www/bitlab-admin/`,
nginx site fajl u `/etc/nginx/sites-available/bitlab-ai`. Vidi
`deploy/README.md` Sekcija 0 za kompletan checklist.

**Princip:** ne pravimo novi standard kad već postoji. Server-side Claude
prilagođava artefakte, lokalna sesija ih samo priprema kao polazište.

### Artefakti koje ova sesija isporučuje

```
scripts/deploy.sh                # bash one-shot install/update na serveru
deploy/bitlab-ai.service         # systemd unit fajl
deploy/nginx-site.conf           # nginx site (snippet ili full)
deploy/README.md                 # checklist za server-side Claude
```

`scripts/deploy.sh` koraci:
1. Detect / create venv u `/opt/bitlab-ai/.venv`
2. `pip install -e .` + CPU-only torch
3. `python scripts/init_db.py` (idempotentno)
4. Build dashboard ako Node postoji na serveru, inače očekuje
   pre-built `dashboard/dist/` koji je rsync-ovan ručno
5. Symlink `dashboard/dist/` na `/var/www/bitlab-admin/`
6. Reload nginx ako je konfig promijenjen, restart bitlab-ai service
7. Smoke test: curl /healthz + /api/dashboard/stats sa Bearer key-em

`deploy/README.md` ima precizne korake koje server-side Claude izvršava:
- SSH preduslove (assumes git već pulled, env već popunjen)
- Prvi install vs update flow
- Rollback procedura (git checkout previous tag, rerun deploy.sh)

### DoD Sesije 5 (lokalna)
- [ ] `scripts/deploy.sh` napisan i `bash -n` ga validira
- [ ] `deploy/bitlab-ai.service` ima User=, WorkingDirectory=, ExecStart= sa pravim putanjama, Restart=on-failure
- [ ] `deploy/nginx-site.conf` ima location blokove za `/admin/`, `/api/`, `/public/`, root i SSL preduslove
- [ ] `deploy/README.md` ima:
  - prvi-put install checklist
  - update checklist (samo `git pull && bash scripts/deploy.sh update`)
  - rollback
  - lista env vars koje moraju biti popunjene (ANTHROPIC_API_KEY, DASHBOARD_API_KEY, AZURE_*, GROQ_*)
- [ ] PR opis pominje da je deploy server-side; daje link na `deploy/README.md`

### DoD server-side sesije (kasnije, druga subscripcija)
- [ ] `https://<domain>/healthz` ok sa drugog uređaja
- [ ] `https://<domain>/admin/` učita dashboard
- [ ] systemd `bitlab-ai.service` enabled i radi
- [ ] nginx site enabled, SSL valid, reload bez errora
- [ ] Bar 1 chat upit zalogovan kroz `/admin/live`
- [ ] Compare side-by-side radi end-to-end

---

## 9. Sesija 6 — Smoke + PR (Sonnet 4.6, low, 30m)

1. `pytest` lokalno + na produkciji.
2. `evals/run.py` + `evals/run_categories.py`.
3. Manualni smoke (5 min): chat, voice, email, compare.
4. README dodaje sekcije "Dashboard", "Compare", "Categories".
5. PR opis sa screenshot-ovima i Test plan-om.

---

## 10. Definition of Done — uslovi za merge na `main`

- [ ] **P0** Sesija 1 DoD (kategorije, eval ≥80%)
- [ ] **P0** Sesija 2 DoD (logging backend, tool_calls)
- [ ] **P0** Sesija 3 DoD (dashboard frontend, 6 stranica, build prolazi)
- [ ] **P0** Sesija 4 DoD (voice UX)
- [ ] **P0** Sesija 5 DoD (deploy)
- [ ] `pytest` zelen
- [ ] Bez `print(...)` debug ostataka
- [ ] Bez committed `.env`, `var/*.db`, `node_modules/`, `dashboard/dist/`
- [ ] PR opis ima Test plan sekciju
- [ ] Reuse iz `playwright-router`-a atribuiran u README-u

---

## 11. Vremenska tabla i stop-loss

| Vrijeme | Aktivnost | Stop-loss |
|---|---|---|
| 10:00–10:15 | Sesija 0 — branch + plan (✅) | — |
| 10:15–11:30 | Sesija 1 — kategorije (Opus high) | u 11:30 mora biti eval ≥70% |
| 11:30–12:30 | Sesija 2 — dashboard backend (Opus high) | u 12:30 `requests` + `tool_calls` writeable |
| 12:30–13:45 | Sesija 3 — dashboard frontend (Opus high) | u 13:45 barem Live + RequestDetail vidljivi |
| 13:45–14:35 | Sesija 4 — voice UX (Sonnet med) | u 14:35 vizuelno ok |
| 14:30 | **STOP-LOSS CHECK** | ako Sesija 3 nije gotova: backend + Live ostaje, ostalo WIP |
| 14:35–15:35 | Sesija 5 — deploy (Sonnet med) | u 15:35 smoke ok |
| 15:35–16:00 | Sesija 6 — PR opis + buffer | — |
| 16:00 | 🎤 Prezentacija | — |

---

## 12. Mini risk register

| Rizik | Vjer. | Impact | Plan B |
|---|---|---|---|
| Kategorije ispod 80% | sred | visok | Spustiti prag na 70%, dodati 5–10 ručnih korekcija u prompt |
| `tool_calls` schema pukne | nis | visok | Opus radi planning prije implementacije |
| Frontend port (Vite/React) padne na verzionim deps | nis | sred | Lock package.json verzije iz playwright-routera 1:1 |
| `/api/dashboard/compare` >8s | sred | nis | Stop-loss; demo sa cached primjerom |
| Deploy puca (nove deps) | nis | visok | Backup demo sa lokalnog laptopa preko ngroka |

---

## 13. Šta NIJE u skopu (post-prezentacija)

- WS streaming logova
- Templates / Compose / Adapters / Health stranice
- Per-token streaming
- Postgres migracija
- Budget tracker + alerti
- Mobilna optimizacija dashboard-a
- Multi-tenant
