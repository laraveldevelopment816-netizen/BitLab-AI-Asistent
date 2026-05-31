# Šta je urađeno na `production-prep` grani (vs `main`)

> 28 commit-ova, 86 fajlova, +15.671 / −465 linija.

## Funkcionalno (chat / voice / email)

- AI klasifikacija namjere — `data/categories.json` (top 30 kategorija, 81.5% kataloga), Claude bira `category_id` u jednom API pozivu, `rag.search()` hard filter
- Sonnet 4.6 kao default za chat (Haiku izbačen — typo halucinacije + "nema laptopa" laž kad lager ima 50)
- Typo robustnost u promptu: "lapatovoe", "tastruru", "monjitor" → ispravna kategorija
- Topao custom build poziv kad katalog nema (umjesto suvog "nemamo")
- Email šablon sa pre-popunjenim `mailto:` linkom (subject + body placeholder-i)
- `escalate_to_human` šalje **pravi email** kroz SMTP ako je konfigurisan (umjesto laži "tim obaviješten")
- Graceful API error handling (400 credit / 429 rate / network) — UI dobije kontakt prodaje, voice dobije TTS-friendly clean varijantu

## Logging dashboard (zasebna React + Vite + TS aplikacija)

- 6 stranica: Live (polling 5s), History, Compare (haiku ↔ sonnet paralelno), RequestDetail (timeline tool calls), Stats (by-channel × by-model), Settings
- Backend: SQLAlchemy async + SQLite, tabele `requests` (sa `session_id` poljem) + `tool_calls`, 7 endpointa pod `/api/dashboard/` sa Bearer auth
- `POST /compare` fan-out kroz `asyncio.gather`
- **`GET /sessions` + `GET /sessions/:id`** — thread view, agregat + turn-by-turn detail
- Tracker u `agent.py` snima svaki tool call sa `input_json`, `output_text`, `latency_ms` (fine-grained, ne black-box)
- Klijent (widget.js) generiše UUID session ID, dijeli između chat i voice mode-a (sessionStorage)
- 7 stranica frontend: **Sessions (default home)**, SessionDetail, Live, History, Compare, RequestDetail, Stats, Settings

## Voice widget UX

- Fullscreen orb na otvaranje → animirano skupljanje u kompaktan header (~25%) kad stigne prvi rezultat, body (~75%) prima product cards
- Thinking sound "tunu nu" pattern (110/165/247 Hz + sub-oktave 55/82/123 Hz, isprekidan ritam)
- Scroll-to-top za bot odgovore (i u chat-u i u voice-u) — prvi rezultat na vrhu
- Markdown table strip + `<voice>` tag strip + `---` separator strip (defensive layeri)
- Multi-line product card prepass (slika + naziv + cijena u različitim redovima → single-line)

## Slike (data quality)

- `scripts/audit_missing_images.py` — paralelni HEAD check; pun audit pokazao 374 / 5.177 = 7.2% missing
- `rag.search()` postavlja `image_url=None` za legacy cover prefix (`728_lenovo.jpg`) i sifre u `missing_images.json`

## TTS cijene

- "1.936 KM" više se ne čita kao "jedna marka" — fix u `_normalize_for_tts` (tačka kao separator hiljada)

## Testovi

- pytest 56 prošli (unit), + 10 markirani `anthropic_api` (integration)
- Node 10 testova za `collapseMultiLineProducts`
- Eval `evals/run_categories.py`: 41/41 = **100%** (sa Sonnet-om)
- Eval `evals/run_format.py`: provjerava raw Claude output bez `---`, `<voice>`, table

## Deploy

- `DEPLOY.md` — 16 linija, copy-paste 8 komandi
- `deploy/bitlab-ai.service` (systemd unit šablon), `deploy/nginx-site.conf` (full nginx site)
- `scripts/deploy.sh` (install/update/rebuild/restart)
- Kompatibilan sa Ivanovim `DEPLOY_GUIDE.md` Pattern A (`/home/ai/`, symlink releases)

## Dokumentacija / planovi

- `PRODUCTION-PREP-PLAN.md` — Sesija 8 plan + DoD
- `MODEL-EVAL-PLAN.md` — Sesija 9 (multi-provider eval kroz sedmicu)
- `GROWTH-PLAN.md` — Sesija 10 (SEO + content + ads + AI growth tool)
- `README.md` — refreshovan, tabela rezolucija na vrhu
- `PLAN.md` (zastario) → DEPRECATED zaglavlje

---

## Prostor za unapređenje

- **Server-side install** — dokumentacija je gotova, fizički deploy na `aiasistent-prod` čeka
- **Webshop integracija** — `<script src=...widget.js>` na `webshop.bitlab.rs`, plus CSP exception ako treba
- **n8n** — nije migriran sa cloud-a na lokalni instalirani n8n (vidi `HOSTING.md` Sekcija 6)
- **Backup strategija** — SQLite `var/bitlab.db` raste, treba dnevni `sqlite3 .backup` cron
- **Monitoring + alerts** — healthcheck cron, alert na error rate > 10%, cost alert na potrošnju
- **Multi-provider eval** (Sesija 9) — testirati GPT-4o-mini, Llama 3.x, DeepSeek-V3 na našem eval setu kroz sedmicu, ekonomska odluka kraj sedmice
- **Growth track** (Sesija 10) — pokrenuti Faza 0 (analytics baseline), pa tehnički + kompetitivni audit
- **Embedding model lazy load** — prvi `/api/chat` traje 30-50s na cold start; predlog: warm-up u `lifespan` task-u sa explicitnim preload-om umjesto background asyncio task-a
- **Per-token streaming** — trenutni MVP nema streaming; korisnik vidi "Razmišljam..." dok cijeli odgovor ne stigne
- **Mobilna optimizacija dashboard-a** — trenutno se gleda na laptopu
- **Adapter za Grok kao chat model** — sada samo STT
- **Compare panel proširenje** — sada haiku/sonnet, treba i GPT/Llama/DeepSeek poslije Sesije 9
- **Health endpoint** za browser-friendly status page
- **Image regeneracija audit-a** kao cron — webshop dodaje proizvode, kategorije se mijenjaju, missing slike isto
- **A/B testing framework** za product page varijante (Sesija 10 Faza 5+)

---

## Objašnjenje

Glavni cilj `production-prep` grane je bio da chat asistent bude **production-ready za demo prezentaciju** — ne više MVP. Sesija 8 je pokrila tri velika smjera koji su nedostajali:

1. **Pouzdanost** — AI više ne halucinira o zalihama, ne ostavlja raw markdown sintaksu, ne tvrdi neistine ("tim je obaviješten"). Default model je Sonnet 4.6 jer Haiku nije imao discipline za realan B2C saobraćaj. Production iteracije se sada vide kroz dashboard, ne treba čitati journal log po log.

2. **Mjerljivost** — fine-grained logging dashboard sa tool call timeline-om je naš diferencijator vs konkurencija. Umjesto "AI je nešto rekao", vidi se tačno koje tool-ove je pozvao, sa kojim parametrima, koliko je trajalo, koliko je koštalo. Compare panel mjeri haiku vs sonnet na realnim upitima.

3. **Operativni hardening** — graceful API error fallback, missing image filter, voice UX redesign, deploy artefakti za server-side install. Sve hot fixovi iz live demo-a su zatvoreni regression testovima da se ne ponove.

Sledeći fokus (post-merge) ide u dva paralelna track-a: **model eval kroz sedmicu** (Sesija 9 — testiramo GPT mini, Llama, DeepSeek za potencijalno jeftiniji production stack) i **growth automatizacija** (Sesija 10 — SEO + content + link building + AI asistent kao newsletter / cart recovery alat). Server install je preduslov oba.
