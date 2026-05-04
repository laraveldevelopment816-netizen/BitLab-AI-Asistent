# BitLab AI Asistent

> Multi-channel AI prodajni asistent za **webshop.bitlab.rs** sa fine-grained logging dashboard-om za optimizaciju AI workflow-a.

```
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI backend (Python 3.11+, async)                          │
│                                                                 │
│  Public:                          Dashboard (Bearer auth):      │
│    /api/chat   chat + voice        /api/dashboard/requests      │
│    /api/email  n8n webhook         /api/dashboard/requests/:id  │
│    /api/stt    Groq → Azure        /api/dashboard/stats         │
│    /api/tts    Azure → edge-tts    /api/dashboard/errors        │
│                                    /api/dashboard/compare       │
│                                                                 │
│  Agent loop (Claude tool use, max 5 iter):                      │
│    search_products(query, category_id?, max_price_km?, top_k?)  │
│    get_faq(topic)                                               │
│    check_availability(sifra)                                    │
│    escalate_to_human(reason, summary)                           │
└─────────────────────────────────────────────────────────────────┘
       ▲              ▲             ▲                  ▲
   ┌───┘              │             │                  │
┌──────────┐ ┌────────────────┐ ┌──────────────┐ ┌────────────────┐
│ Widget   │ │ Voice mod      │ │ n8n Email    │ │ Dashboard SPA  │
│ widget.js│ │ (header 25%/   │ │ IMAP→/email  │ │ React+Vite+TS  │
│          │ │  results 75%)  │ │ →SMTP reply  │ │ /admin/        │
└──────────┘ └────────────────┘ └──────────────┘ └────────────────┘

Knowledge base + storage:
  data/products.index.npz   5.278 vektora, MiniLM-L12-v2 (multilingual)
  data/products.meta.json   meta (ime, cijena, kolicina, URL, sifra)
  data/categories.json      top 30 kategorija sa labelama (Sesija 8)
  data/category_terms.json  build-time prefix + soft-boost (legacy)
  data/faq.md               ručno kurirane sekcije
  var/bitlab.db             SQLite — requests + tool_calls
```

---

## Šta je novo (Sesija 8 — production prep)

| Stavka | Status |
|---|---|
| **AI klasifikacija namjere** sa hard category filter (eval **100%** na Sonnet 4.6) | ✅ |
| **Sonnet 4.6 default za chat** (Haiku izbačen — vidi *Modelska odluka* ispod) | ✅ |
| **Typo robustnost** + regression test set (`tests/test_typo_robustness.py`) | ✅ |
| **Logging dashboard** (React + Vite + TS, 6 stranica) sa fine-grained tool call timeline | ✅ |
| **Compare endpoint** — fan-out istog upita kroz haiku ↔ sonnet paralelno | ✅ |
| **Voice widget UX** — kompaktan header 25% + body 75% za rezultate | ✅ |
| **Deploy artefakti** (`scripts/deploy.sh`, `deploy/*.service`, nginx, README) | ✅ |
| Server-side install na produkciju (zasebna sesija, vidi `deploy/README.md`) | 🟡 čeka |

PR: `production-prep` → `main`. Detalji u `PRODUCTION-PREP-PLAN.md`.

> **🔬 Otvorena rezolucija (Sesija 9, sedmica 2026-05-05 → 2026-05-11):**
> Sonnet 4.6 je *trenutni* default, ne *konačna* odluka. Ova sedmica je
> dedikovana **multi-provider eval-u** (Claude Haiku/Sonnet/Opus, GPT-4o-mini,
> Llama 3.x, DeepSeek-V3) sa target-om ≥99% pass rate i ekonomskom odlukom
> kraj sedmice. Plan, kandidati, metodologija i timeline u
> **`MODEL-EVAL-PLAN.md`**. Ivanova subjektivna hipoteza ("GPT mini će
> završiti priču sa potrošnjom kao Haiku") tu je eksplicitno odvojena od
> stvarnog rezultata — testiramo, pa odlučujemo.

> **📈 Otvorena rezolucija (Sesija 10, kontinuirano od 2026-W19):**
> Iskorišćavamo Claude Max plan za **growth automatizaciju** —
> dubinski tehnički + kompetitivni SEO audit, content production,
> link building outreach, paid ads automatizaciju i AI asistent kao
> growth tool (newsletter, cart recovery, review requests). Cilj:
> +50% organic / +20 referring domains u 90 dana, +150% / +60 u 180.
> Plan, faze, KPI-jevi i schedule u **`GROWTH-PLAN.md`**. Ne radimo
> black-hat / spam / fake reviews — sve je human-in-the-loop.

### Modelska odluka — zašto Sonnet 4.6 za chat (a ne Haiku)

Tokom production smoke testa pojavile su se dvije ozbiljne mane Haiku-a 4.5
koje eval set nije hvatao do tog trenutka:

1. **Pojašnjenje umjesto pretrage na typo upite.** Realni korisnik kuca brzo
   i pravi tipove. Haiku na "Imate li **lapatovoe**" (typo za "laptop")
   tražio je pojašnjenje umjesto da pozove `search_products(category_id=98)`,
   iako je sistem prompt eksplicitno zabranjivao pojašnjenja za očigledne
   tipove proizvoda.
2. **Halucinacija nakon search-a.** U sledećem turu, na "Laptop", Haiku je
   rekao *"Nažalost, trenutno nemamo dostupnih laptopa u katalogu"* — laž,
   katalog ima 50 laptopa u cat 98, a tool je vratio rezultate.

Ovo nije promptable bug — Haiku jednostavno **ne sluša pravila pouzdano** za
production-grade B2C asistenta. Sonnet 4.6 sa istim promptom prošao je sve
typo i halucinacijske testove (eval 41/41 = 100%, plus 6/6 dedikovanih
regression testova u `tests/test_typo_robustness.py`).

**Cost/latency tradeoff:** Sonnet je ~3× skuplji input, ~3× skuplji output i
~2× sporiji od Haiku-a. Za naš volumen (~1.000 chat upita/mj) razlika je
~$1.20/mj — prihvatljivo za pouzdanost. Compare panel u dashboard-u i dalje
omogućava paralelno testiranje haiku ↔ sonnet na istom upitu (vidi *Sloj 1*
ispod), pa kad Anthropic isporuči Haiku 5 ili manji model dovoljno
discipliniran, lako prebacujemo natrag (`CHAT_MODEL` env var override).

---

## Struktura projekta

```
bitlab-ai-asistent/
├── app/
│   ├── main.py            # FastAPI + lifespan (RAG preload, init_db)
│   ├── agent.py           # Claude tool-use loop, vraća _trace dict za logging
│   ├── tools.py           # 4 tool-a: search_products + get_faq + check_availability + escalate
│   ├── rag.py             # Hibrid: BM25 (0.4) + vektor (0.6) + hard category filter
│   ├── faq.py             # FAQ keyword retrieval po sekcijama
│   ├── system_prompts.py  # 3 prompta: chat / voice / email + klasifikaciono pravilo
│   ├── email_poller.py    # IMAP fallback (rezerva za n8n)
│   ├── config.py          # Pydantic Settings, čita .env
│   ├── server/
│   │   └── dashboard.py   # /api/dashboard/* (Bearer auth, JSON API + compare)
│   └── storage/
│       ├── db.py          # async SQLAlchemy engine + sessionmaker
│       ├── models.py      # Request + ToolCall (sa FK)
│       └── repo.py        # insert + get helper-i (best-effort)
├── dashboard/             # React 19 + Vite 8 + TS — 6 stranica (Live, History,
│   ├── src/pages/         # Compare, RequestDetail, Stats, Settings)
│   ├── src/components/    # Layout (sidebar 232px), atoms (Tag, Btn, Metric...)
│   ├── src/api.ts         # axios client + Bearer interceptor (localStorage)
│   ├── src/tokens.ts      # dark theme + BitLab orange + per-channel/model boje
│   └── package.json       # react-router 7, TanStack Query, axios, tailwind 4
├── deploy/                # Server-side install artefakti (Sesija 5)
│   ├── README.md          # ⚠️ TAČKA 0 — server hostuje 4 druge aplikacije
│   ├── bitlab-ai.service  # systemd unit (User=bitlab, venv ExecStart)
│   └── nginx-site.conf    # full nginx site (HTTPS, /admin/, /api/, gzip)
├── scripts/
│   ├── embed_products.py    # JEDNOKRATNO: products.index.npz + meta.json
│   ├── build_categories.py  # Generiše data/categories.json (Sesija 1)
│   ├── init_db.py           # Idempotentno kreira requests + tool_calls tabele
│   ├── deploy.sh            # Server-side: install/update/rebuild/restart
│   └── smoke_test.py        # 4 chat upita end-to-end
├── evals/
│   ├── test_questions.json  # Originalni eval set (Sesija 4)
│   ├── run.py               # Originalni eval runner
│   ├── category_eval.json   # 36 upita za AI klasifikaciju (Sesija 1)
│   └── run_categories.py    # Mjeri top-1 category_id accuracy
├── public/
│   ├── widget.html        # Demo BitLab webshop
│   ├── widget.js          # Embeddable chat + voice widget
│   └── voice.html         # Voice mod standalone demo
├── n8n/
│   └── email-autoreply.json
├── data/
│   ├── all-products.json     # Sirovi katalog (phpMyAdmin export)
│   ├── faq.md
│   ├── categories.json       # Sesija 8 — top 30 kategorija sa labelama
│   ├── category_terms.json   # Build-time prefix + soft-boost terms
│   ├── products.index.npz    # ❌ gitignore — generiše embed_products.py
│   └── products.meta.json    # ❌ gitignore — generiše embed_products.py
├── var/                   # ❌ gitignore — bitlab.db i runtime
├── tests/                 # pytest, 19 testova
├── PRODUCTION-PREP-PLAN.md  # Sesija 8 plan + DoD
├── BITLAB-MVP-PLAN.md       # Originalni MVP plan (Sesije 0–7)
├── HOSTING.md             # Detaljan VPS vodič (legacy reference)
├── PLAN.md                # ⚠️ DEPRECATED (Node.js verzija iz aprila)
├── .env / .env.example
└── pyproject.toml
```

---

## Preduslovi

| Alat | Verzija | Zašto |
|---|---|---|
| Python | 3.11+ | FastAPI lifespan + async SQLAlchemy |
| pip | bilo koja | install -e . |
| Node.js + pnpm | 20+ | **samo za dashboard build** (nema Node u runtime-u) |
| nginx + certbot | bilo koja | server-side deploy |

Rad na **WSL2** (Windows), Linux ili macOS.

---

## 1. Postavljanje projekta

### Kloniranje

```bash
git clone https://github.com/laraveldevelopment816-netizen/BitLab-AI-Asistent.git
cd BitLab-AI-Asistent
```

### Python venv

```bash
python3 -m venv .venv
source .venv/bin/activate
```

> **⚠️ WSL2 napomena (kritično za startup brzinu):** ako je projekat na `/mnt/c/...`,
> Python import preko 9p protokola je **5–10× sporiji** nego na native Linux FS.
> sentence-transformers ima ~180 .py fajlova → import može trajati 50+ sekundi.
>
> **Rješenje:** drži `.venv` izvan `/mnt/c`:
> ```bash
> python3 -m venv ~/.venvs/bitlab
> source ~/.venvs/bitlab/bin/activate
> ```
> Kod (sa `/mnt/c`) može ostati gdje jeste — samo venv treba biti na ext4.

### Instalacija zavisnosti

```bash
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu
```

Šta dolazi:
- **torch CPU** (~200MB) umjesto CUDA wheel-a (~1.2GB)
- **sentence-transformers <4** — bez `sparse_encoder` modula (v5.x dodaje ~30s import)
- **anthropic, faster-whisper, edge-tts, httpx**
- **sqlalchemy[asyncio] + aiosqlite** — dashboard storage (Sesija 8)

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"  # False ✓
```

> Opciono za pull iz MySQL baze: `pip install -e ".[mysql]"`

### Node + pnpm (za dashboard)

```bash
# Ubuntu/WSL2
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt-get install -y nodejs
sudo npm i -g pnpm
```

---

## 2. API ključevi i .env

```bash
cp .env.example .env
```

```env
# ── Anthropic (OBAVEZNO) ─────────────────────────────────────
# console.anthropic.com → API Keys
ANTHROPIC_API_KEY=sk-ant-api03-...

# Default modeli (override opciono):
# Sesija 8: Haiku izbačen sa chat-a — ne sluša pravila pouzdano
# (typo upiti → pojašnjenje umjesto pretrage; halucinacije o zalihama).
# Vidi "Modelska odluka" sekciju iznad i tests/test_typo_robustness.py.
# CHAT_MODEL=claude-sonnet-4-6             # chat + voice — pouzdan
# EMAIL_MODEL=claude-sonnet-4-6            # email + compare drugi pol

# ── TTS / STT ─────────────────────────────────────────────────
# Azure Speech: portal.azure.com → "Speech Services" (Free F0 tier).
# Pokriva i TTS i STT istim ključem. Najbolji kvalitet za bs/hr/sr.
AZURE_SPEECH_KEY=
AZURE_SPEECH_REGION=westeurope
AZURE_STT_LANGUAGE=hr-HR
TTS_VOICE=hr-HR-GabrijelaNeural

# Groq Whisper STT (opciono fallback, besplatno 7200s/dan)
# console.groq.com → API Keys → Create
GROQ_API_KEY=

# ── Dashboard / logging (Sesija 8, OBAVEZNO za /admin/) ──────
# Generiši: python -c "import secrets; print(secrets.token_urlsafe(32))"
DASHBOARD_API_KEY=

# ── IMAP/SMTP (rezerva ako n8n cloud zataji) ─────────────────
IMAP_HOST=imap.gmail.com
IMAP_USER=
IMAP_PASSWORD=
SMTP_HOST=smtp.gmail.com
SMTP_USER=
SMTP_PASSWORD=

# ── Webshop ──────────────────────────────────────────────────
WEBSHOP_BASE_URL=https://webshop.bitlab.rs
```

> **Format:** koristi `=`, ne `:`. Bez navodnika oko vrijednosti.

---

## 3. Vektorska baza i kategorije (jednokratno)

### 3.1 Embeddings za 5.278 proizvoda

```bash
python scripts/embed_products.py
```

Trajanje: 3–5 min (prvi put skida ~120MB MiniLM-L12-v2 model). Output:

```
✓ Sačuvano: data/products.index.npz   (~7.2 MB)
✓ Sačuvano: data/products.meta.json   (~4.5 MB)
```

> Oba fajla su u `.gitignore` — svaki dev ih generiše lokalno.

### 3.2 Kategorije (Sesija 8 — AI klasifikacija)

```bash
python scripts/build_categories.py
```

Output:

```
✅ data/categories.json — top 30 kategorija
   Pokrivenost: 4,304 / 5,278 (81.5%)
```

### 3.3 Inicijalizacija dashboard DB

```bash
python scripts/init_db.py
```

Idempotentno — kreira `var/bitlab.db` sa tabelama `requests` i `tool_calls`.

### 3.4 Smart matching: tri sloja klasifikacije

Korisnici nisu uvijek precizni ("trebam nešto za kucanje", "imate li laptopov", "treba mi disk za laptop"). Sistem rješava namjeru u tri komplementarna sloja:

#### Sloj 1 — AI klasifikacija namjere (primarno, Sesija 8) ⭐

`data/categories.json` sadrži **top 30 kategorija** sa human-readable labelama, koje pokrivaju 81.5% kataloga:

```json
{
  "98":  {"label": "Laptopi i notebook računari", "count": 50, "examples": [...]},
  "220": {"label": "Tastature", "count": 99, ...},
  "277": {"label": "Miševi", "count": 535, ...},
  "394": {"label": "Maske, futrole i zaštitna stakla za telefone", ...}
}
```

Kategorije se utiskuju u `search_products` tool description **i** kao `enum` na `category_id` parametru. Claude vidi listu pri svakom pozivu i sam klasifikuje upit u jedan ID — **single-call** flow:

```
korisnik: "trebam nešto za kucanje"
  ↓
Claude (jedan API poziv) → search_products(query="tastatura", category_id="220")
  ↓
rag.search() → hard filter na 99 tastatura, hibridni rang unutar kategorije
```

Eval: **100%** top-1 accuracy na 41 realnom upitu (`evals/run_categories.py`),
uključujući 5 typo cases ("lapatovoe", "laptopov", "telfon", "tastruru",
"monjitor") koji su prije pucali sa Haiku-om.

**Regenerisanje:** `python scripts/build_categories.py` čita `products.meta.json` i regeneriše `data/categories.json`. Manuelni labeli su u `LABELS` dict-u u skripti — tu dopuni nove kategorije ako se pojave u top 30. Auto-fallback heuristika (najčešći leading bigram/monogram) pokriva nepoznate.

#### Sloj 2 — Build-time prefix (`data/category_terms.json`)

Mapiranje kategorija → terminima koji nisu u imenima proizvoda te kategorije. U `embed_products.py` se prefix ponavlja 3× u `search_text` polju → embedding razumije "laptop" iako su u imenu samo brendovi (Acer Nitro, Lenovo IdeaPad). Ovo pomaže semantičkom retrieval-u **unutar** odabrane kategorije.

#### Sloj 3 — Search-time soft boost (fallback)

Ako Claude **ne pošalje** `category_id` (npr. brand+model upit "Patriot SSD 240GB"), `rag.py` i dalje pokušava intent detekciju iz `category_terms.json` i daje +0.25 boost match-ed proizvodima — sprečava accessory šum kad AI nije bio siguran. Kad je `category_id` zadat, hard filter ima prednost i soft boost se preskače.

**Kad dodati novu kategoriju u top 30:** dopuni `LABELS` dict u `scripts/build_categories.py`, pokreni skriptu, dodaj 1–2 reprezentativna upita u `evals/category_eval.json`, ponovo `python evals/run_categories.py`.

---

## 4. Pokretanje (lokalno dev)

### Backend

```bash
uvicorn app.main:app --reload
```

Server sluša na `http://localhost:8000`.

**Provjera zdravlja:**

```bash
curl http://localhost:8000/healthz
```

```json
{
  "status": "ok",
  "chat_model": "claude-haiku-4-5-20251001",
  "email_model": "claude-sonnet-4-6",
  "embed_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
  "products_index_present": true,
  "products_meta_present": true,
  "faq_present": true
}
```

Swagger UI: `http://localhost:8000/docs`

### Dashboard (drugi terminal)

```bash
cd dashboard
pnpm install
pnpm dev    # Vite na :5173 sa proxy /api/* → :8000
```

Otvori `http://localhost:5173/admin/`, idi na **Settings**, paste-uj `DASHBOARD_API_KEY` iz `.env`, save → svi tabovi rade.

---

## 5. Demo — četiri kanala + dashboard

### 5.1 Chat widget

`http://localhost:8000` (ili direktno `http://localhost:8000/public/widget.html`)

Embed na bilo koji sajt:
```html
<script src="https://ai.bitlab.rs/public/widget.js"></script>
```

### 5.2 Voice mod

Otvori u **Chrome ili Edge** (Firefox ne podržava Web Speech API):
```
http://localhost:8000/public/voice.html
```

UX (Sesija 8): kompaktan header (orb + state + wave inline, ~25% panela), body sa product cards (~75%) — auto-scroll, isti markdown renderer kao chat. Mobilni breakpoint preserved.

### 5.3 Chat API (curl)

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Imate li gaming mis", "channel": "chat"}'
```

### 5.4 Email API (curl, n8n format)

```bash
curl -X POST http://localhost:8000/api/email \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "kupac@example.com",
    "subject": "Upit za SSD diskove",
    "body": "Pozdrav, zanima me imate li SSD 1TB i koja je dostava?"
  }'
```

### 5.5 Dashboard /admin/

Otvori `http://localhost:5173/admin/` (dev) ili `https://<domain>/admin/` (prod):

- **Live** — polling 5s, fresh-row highlight, pause/resume; klik na red → RequestDetail
- **History** — paginated, filteri po channel/status
- **Compare** — paste upit → fan-out kroz haiku + sonnet paralelno → side-by-side rezultati sa latency, tokens, cost, tool call summary
- **RequestDetail** — top metrike, prompt, **timeline svakog tool call-a** (expand/collapse: input JSON, output text, latency badge), final response
- **Stats** — total + by-adapter (channel × model) breakdown
- **Settings** — input za API key + env diagnostika

### 5.6 Compare API (curl)

```bash
curl -X POST http://localhost:8000/api/dashboard/compare \
  -H "Authorization: Bearer $DASHBOARD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "imate li tastaturu", "channel": "chat", "models": ["haiku", "sonnet"]}'
```

---

## 6. Smoke test + eval

```bash
# Pokreni server u jednom terminalu, pa:

# 4 standardna upita end-to-end
python scripts/smoke_test.py

# Pytest unit + integration (19 testova)
python -m pytest tests/ -q

# AI klasifikacija eval (36 upita, target ≥80%)
python evals/run_categories.py
```

Trenutni baseline: **94.4%** (34/36) na threshold 80%.

---

## 7. n8n Email Auto-Reply

n8n radi **lokalno** na istoj mašini kao FastAPI — `/api/email` nije izložen javnom internetu.

```
┌─────────────────────────────────────────────────┐
│  Tvoja mašina (laptop / VPS)                    │
│  n8n (localhost:5678) ──► localhost:8000        │
│  Gmail trigger           (FastAPI /api/email)   │
└─────────────────────────────────────────────────┘
```

### Opcija A — n8n Desktop (lokalni demo)

1. [n8n.io/download](https://n8n.io/download) → instaliraj
2. Pokreni → otvori `http://localhost:5678`
3. **New Workflow → Import from JSON** → `n8n/email-autoreply.json`
4. U **HTTP: Pitaj AI Asistenta** nodu URL: `http://localhost:8000/api/email`
5. **Credentials → New → Gmail OAuth2** → Sign in with Google
6. **Activate** workflow

### Opcija B — n8n Docker (VPS / produkcija)

```bash
docker run -d --name n8n --restart always \
  -p 5678:5678 -v n8n_data:/home/node/.n8n \
  n8nio/n8n
```

URL u HTTP nodu: `http://host.docker.internal:8000/api/email` (za Docker), inače `localhost`.

### Fallback — IMAP poller

```bash
python -m app.email_poller   # polluje INBOX svakih 60s
```

---

## 8. Troškovi (procena za 1.000 chat upita / mjesec)

| Servis | Plan | Cijena | Procena |
|---|---|---|---|
| Claude Sonnet 4.6 (chat + voice + email) | Pay-as-you-go | $3/$15 per 1M | ~$2.40 |
| Claude Haiku 4.5 (samo Compare drugi pol za A/B testing) | Pay-as-you-go | $1/$5 per 1M | ~$0.20 |
| Azure Speech (TTS + STT) | Free tier | $0 | 500K znakova/mj TTS + 5h STT |
| Groq Whisper (fallback STT) | Free tier | $0 | 7.200s/dan |
| Sentence-transformers + faster-whisper | Lokalno | $0 | $0 uvijek |
| n8n (lokalni Docker) | Self-hosted | $0 | bez limita |
| VPS (Ubuntu, 2 vCPU / 2 GB RAM) | npr. Hetzner CX22 | ~€4 | fixna |
| **Ukupno** | | | **~€6–9/mj** |

Stvarni troškovi po requestu su vidljivi u **Stats** tab-u dashboard-a (cumulative + by-adapter).

---

## 9. Česti problemi

| Problem | Rješenje |
|---|---|
| Server ne starta — `products.index.npz` nedostaje | `python scripts/embed_products.py` |
| `anthropic.AuthenticationError: invalid x-api-key` | `.env` format mora biti `KEY=value` (sa `=`, bez navodnika) |
| `Your credit balance is too low` | [console.anthropic.com](https://console.anthropic.com) → Plans & Billing |
| TTS ne radi — `503` | Postavi `AZURE_SPEECH_KEY` u `.env` ili koristi edge-tts fallback (default radi bez ključa) |
| Voice HTML — mikrofon ne radi | Web Speech API podržavaju samo Chrome i Edge |
| `ModuleNotFoundError` | Aktiviraj venv: `source .venv/bin/activate` |
| Port 8000 zauzet | `fuser -k 8000/tcp` (Linux) ili `netstat -ano \| findstr :8000` (Windows) |
| `/admin/*` vraća 401 | Unesi `DASHBOARD_API_KEY` u Settings tab → save → reload |
| Dashboard build pada | Provjeri Node 20+ i pnpm; obriši `node_modules/` + `pnpm-lock.yaml` i `pnpm install` |
| Prvi chat poziv vraća error | sentence-transformers preload na WSL2 traje 30–50s; sledeći ide normalno |

---

## 10. Deployment na server (VPS)

> **Server-side install pristup** (Sesija 8): umjesto SSH iz lokalne sesije,
> deploy radi Claude Code instanca **instalirana NA samom serveru** sa
> direktnim shell pristupom. Razlog: efikasnije za buduće mikro-servise
> (n8n migracija, monitoring, dodatni adapteri) bez piping-a kroz lokalni env.

### ⚠️ TAČKA 0 — Server hostuje 4 druge aplikacije

Naš deploy se prilagođava postojećim konvencijama (layout, service user-i,
portovi, nginx struktura, SSL, logging) — NE obrnuto. Server-side Claude
MORA prvo dobiti pravila od Ivana, pa tek onda izvršiti install.

Default-i u artefaktima koji vjerovatno trebaju promjenu:
- `PROJECT_DIR=/opt/bitlab-ai`
- `SERVICE_USER=bitlab`
- Port `127.0.0.1:8000`
- `DASHBOARD_DIST_TARGET=/var/www/bitlab-admin/`
- nginx site u `/etc/nginx/sites-available/bitlab-ai`

Detaljan checklist: **`deploy/README.md`** (Sekcija 0 do 3).

### Brzi update flow (kad je install završen)

```bash
ssh server
cd /opt/bitlab-ai
sudo bash scripts/deploy.sh update
```

Komanda radi: `git pull` → reinstall deps → regenerate `categories.json` →
init DB (idempotentno) → rebuild dashboard → publish u nginx folder →
restart `bitlab-ai.service` → smoke test.

Ostale komande:
- `sudo bash scripts/deploy.sh install` — prvi install (kreira venv, systemd, nginx)
- `sudo bash scripts/deploy.sh rebuild` — samo dashboard rebuild + publish
- `sudo bash scripts/deploy.sh restart` — samo systemctl restart

### Artefakti

| Fajl | Šta sadrži |
|---|---|
| `scripts/deploy.sh` | Bash one-shot sa install/update/rebuild/restart komandama |
| `deploy/bitlab-ai.service` | systemd unit (User=bitlab, venv ExecStart, ProtectSystem=strict, MemoryMax=900M) |
| `deploy/nginx-site.conf` | Full nginx site (HTTP→HTTPS, SSL, /admin/ alias, /api/ proxy, gzip, body limit 30M za STT) |
| `deploy/README.md` | Server-side checklist, troubleshooting, rollback |

### Widget integracija na webshop

Posle uspješnog deploy-a, na `webshop.bitlab.rs` dodati pred `</body>`:

```html
<script src="https://ai.bitlab.rs/public/widget.js"></script>
```

Stari `HOSTING.md` (manuelni VPS vodič) ostaje u repo-u kao reference za nginx
+ certbot detalje.

---

## 11. Razvoj (kako doprinositi)

### Grane i sesije

| Grana | Status | Šta sadrži |
|---|---|---|
| `main` | stabilno | MVP do Sesije 7 (chat + voice + email + n8n + security review) |
| `production-prep` | u review | Sesija 8: kategorije + dashboard + voice UX + deploy |

Plan po sesijama: **`PRODUCTION-PREP-PLAN.md`** (Sesija 8) i **`BITLAB-MVP-PLAN.md`** (Sesije 0–7).

### Workflow

1. Branch sa `main`, ime u formatu `<sesija>-<short-name>` (npr. `9-monitoring`)
2. Plan dokument na vrhu repo-a sa: model preporuka (Opus high / Sonnet medium), DoD, stop-loss
3. Eval set ako diraš retrieval ili klasifikaciju (`evals/`)
4. Pytest mora biti zelen prije PR-a
5. PR opis ima Test plan sekciju i listu DoD ✅

### Testovi

```bash
python -m pytest tests/ -q                              # unit + integration
python -m pytest tests/ -m "not anthropic_api"          # bez skupih API testova
python -m pytest tests/test_typo_robustness.py -v       # samo typo regression (Sesija 8 hotfix)
python evals/run_categories.py                          # 41 upit, target ≥80%
python scripts/smoke_test.py                            # 4 chat upita end-to-end (server mora raditi)
cd dashboard && pnpm build                              # TS check + Vite build (~1s)
bash -n scripts/deploy.sh                               # bash sintaksa
```

### Modeli — kad koristiti šta

| Zadatak | Model | Razlog |
|---|---|---|
| Arhitekturne odluke (schema, abstraction layers) | **Opus 4.7 high** | Skupo se ispravlja kasnije |
| Port iz drugog repo-a (poznat materijal) | **Opus 4.7 high** | Jedan precizan pass < više iteracija |
| Polish, deploy, smoke, dokumentacija | **Sonnet 4.6 medium** | Obim posla, manje tokena |
| Trivijalne izmjene (typo, bump verzije) | **Sonnet 4.6 low** | — |

---

## 12. Kontakt

**BitLab d.o.o.** · Jevrejska 37, 78000 Banja Luka  
prodaja@bitlab.rs · 066 516 174 · webshop.bitlab.rs  
JIB: 4403711250001
