---
sections:
  - id: now
    name: Now
  - id: next
    name: Next
  - id: later
    name: Later
  - id: completed
    name: Completed
---

# Akcioni plan — bitlab-ai-asistent

Ažurirano: 2026-05-17

> Strateški plan (Now/Next/Later inicijative) za `bitlab-ai-asistent`.
> Schema: [`bitlab-standards/docs/standards/akcioni-plan-schema.md`](../../../bitlab-standards/docs/standards/akcioni-plan-schema.md).
> Taktički nivo (dnevne taske) — [`../../STATUS.md`](../../STATUS.md).
>
> Plan je rekonstruisan reverse-engineering-om iz arhive (taska `rev1` u
> STATUS Doing, korak 2 verifikacija završena 2026-05-17). Izvori i evidence
> iz koda + git log-a: `docs/archives/bitlab-mvp-plan.md`,
> `docs/plans/{production-prep,model-eval,growth}.md`, `docs/changes.md`,
> `docs/reviews/{code-review,security-review}.md`, `LIVE.md`.

## Now

### Produkcijska stabilnost — P1 hotfix + cold-start + stale docs <!-- id:p1fix -->

Sistem je u produkciji nakon LIVE testa 2026-05-08, ali iz
`docs/reviews/code-review.md` ostala su otvorena 4 P1 nalaza koja se
manifestuju pod istovremenim opterećenjem: TOCTOU race (C2 — nema
`threading.Lock` u 4 lazy-singleton helpera), Whisper preload izostao iz
`lifespan`-a (C3 — komentar laže), endpointi bez centralnog exception
handler-a za `anthropic.APIStatusError` (C4). Plus: embedding model
cold-start od 30–50s na prvom `/api/chat`-u, stale dokumentacija
(`security-review.md` body, `bitlab-mvp-plan.md` S7.3, `LIVE.md` Plan B).
n8n `/api/email` migracija je blokirana DNS-om koji Rale treba da publikuje
(workaround paralelno).

Started: 2026-05-17

**Scope:**
- C2/C3/C4 P1 fix-evi (`app/main.py`, `app/rag.py`, `app/agent.py`, `app/tools.py`)
- C7/C8 P2 quality fix-evi (module-scope `_HALLUCINATIONS` kao `frozenset`, lazy API key validacija završetak)
- Cold-start fix — warm-up Whisper + embedding model u `lifespan` umjesto čisto background task-a
- Stale doc cleanup (`security-review.md` body, `bitlab-mvp-plan.md` S7.3 status, `LIVE.md` Plan B)
- n8n DNS workaround (paralelno sa `feature/n8n-deploy` branch-om koja čeka Rale-ov push)

**Out of scope:**
- C9–C11 nice-to-have iz code review-a (Later — `crnth`)
- Multi-provider eval (Next — `meval`)

### Safety-net testovi oko kritične poslovne logike <!-- id:tst1 -->

Sistematski sloj testova (unit + integracioni + regresioni + e2e) koji hvata
regresije prije produkcije. Gradi se na postojećih 8 test fajlova
(`tests/`) + 3 eval runnera (`evals/`) — konsolidacija i popuna rupa, ne
greenfield. Posebno: jedan regresioni test po dokumentovanom prošlom bugu
(typo handling — `test_typo_robustness.py` je obrazac; halucinacija zaliha;
prompt-injection; prazan search → escalate). Komplementarna sa `meval`:
`tst1` mjeri ispravnost koda, `meval` mjeri kvalitet AI ponašanja.

Started: 2026-05-17 (eskalirana iz STATUS taske u inicijativu)

**Scope:**
- Inventar + gap analiza (postojeći testovi/evali vs ključna logika u `app/`)
- Unit — agent loop, RAG hibridni scoring + category/brand filter, FAQ parsiranje, config validatori
- Integracioni — agent loop + tools + rag, dashboard DB sloj (`requests`/`tool_calls`/`sessions`), `/api/dashboard/` endpointi, escalation/SMTP put
- Regresioni — jedan test po dokumentovanom prošlom bugu (izvor `docs/reviews/` + `docs/changes.md`)
- E2E — `/api/chat`, `/api/tts`, `/api/stt`, `/api/email` golden-path
- CI gate — pytest markeri (brzi unit vs spori/`anthropic_api`); mreža je "safety net" tek kad se pokreće automatski

**Out of scope:**
- 100% coverage — fokus su poslovna logika, kritični putevi, prošli bugovi
- Multi-model AI eval — to je `meval`

## Next

### Model eval framework — multi-provider odluka <!-- id:meval -->

Plan Sesije 9 (`docs/plans/model-eval.md`, schedule 2026-05-05 do 11)
prošao bez izvršenja u kodu — `app/models.py` nedostaje, `evals/run_models.py`
nedostaje, compare panel i dalje samo haiku/sonnet, `evals/results/`
prazan. Cilj se ne mijenja: ekonomska odluka o chat modelu na osnovu
podataka, ne intuicije. Multi-provider abstraction, run_models runner,
compare panel proširenje (+GPT-4o-mini, +Llama 3.x, +DeepSeek-V3),
subjektivna Likert ocjena, finalni writeup. Aktivira se nakon što `tst1`
uigra CI okosnicu — tako se eval prag postavlja na ispravnom temelju.

**Scope:** sve podsesije 9.1–9.6 iz `docs/plans/model-eval.md`.

**Otvorena pitanja:** sekcija 8 u izvornom planu (env vars na prod, volumen
projekcija, B2B kanal scope) ostaje otvorena.

### Growth track — analytics baseline + tehnički audit <!-- id:grow1 -->

Plan Sesije 10 (`docs/plans/growth.md`) napisan u `66fadd2`, F0 trebao
da krene 2026-W19 — nije pokrenut, `growth/` folder je prazan. Realističan
prvi korak: Faza 0 (GA4 + Search Console + Bing + Ahrefs trial baseline) +
Faza 1 (tehnički SEO audit — Core Web Vitals, schema.org, internal linking,
AI widget SEO impact). Tek nakon baseline-a se vidi gdje je realan ROI —
Faze 2–6 ostaju Later kao `grow2`.

**Scope:** F0 + F1 iz `docs/plans/growth.md`.

### Uskladiti repo sa bitlab-standards strukturom <!-- id:std1 -->

`docs/README.md` linkuje nazad na bitlab-standards + ostala uskladja prema
standardu. Mala mehanička inicijativa, ne blokira ništa — zatvara dug
standarda. Archive rename (`docs/archive/` → `docs/archives/`) + konsolidacija
istorijskih dokumenata su izvučeni kao zasebna STATUS kartica `arch`.

## Later

### Growth track — link building, paid ads, AI growth tool <!-- id:grow2 -->

Nastavak `grow1` — Faze 2–6 iz `docs/plans/growth.md`: kompetitivni audit,
keyword strategy + content plan, link building outreach, paid ads pilot,
AI asistent kao newsletter/cart recovery alat. Zavisi od `grow1` baseline-a
da bi se znalo gdje je ROI.

### Operativna infrastruktura — backup, monitoring, alerts <!-- id:ops1 -->

Iz `docs/changes.md` "Prostor za unapređenje" liste: dnevni `sqlite3 .backup`
cron za `var/bitlab.db`, healthcheck cron, alert na error rate > 10%, cost
alert na Anthropic potrošnju, `/healthz` browser-friendly status page, image
regeneracija audita kao cron (webshop dodaje proizvode, kategorije se mijenjaju).
Sad nije hitno jer je promet kontrolisan; postaje preduslov kad `grow1` +
`grow2` povećaju saobraćaj.

### UX skalabilnost — streaming, A/B testing <!-- id:uxsc -->

Per-token streaming u widget-u (sad korisnik čeka cijeli odgovor sa
"Razmišljam..."). A/B testing framework za product page varijante — tek
kad imamo 1.000+ posjeta/dan po stranici (zavisi od `grow2`).

### Code review nice-to-haves <!-- id:crnth -->

C9 (`app/tts_utils.py` ekstrakcija — `main.py` se smanjuje sa ~600 linija
na ~330), C10 (`np.load` u `rag.py:156` sa context manager-om), C11
(`_meta_to_url` helper za URL konzistentnost između `rag.search` i
`handle_check_availability`). Ne blokiraju produkciju — "u prolazu" PR-ovi.

### Voice → naruči → email cycle <!-- id:vord -->

Sesija 7.5 — `prepare_order_email(product_sifra, address)` tool koji vraća
strukturirani mailto URL, popunjavanje `[NAZIV_PROIZVODA]` / `[CIJENA]`
placeholder-a u voice kanalu, varijanta `EMAIL_FORMAT`-a za "potvrda
narudžbe primljene". Polish, ne hotfix.

### OpenClaw integracija — monitoring/escalation gateway <!-- id:oclaw -->

Branch `feature/openclaw-integration` ima passthrough gateway iza
`use_openclaw` flag-a (commit `7fcee70`). Ideja: bitlab-ai-asistent eskalira
u OpenClaw personal-agent kao "kritičan signal" → push notification
korisniku. Cilj — vezivanje sa korisnikovim ličnim AI agentom. Nije hitno;
čeka da OpenClaw stabilizuje svoj API u sopstvenom repou.

## Completed

### MVP — chat + voice + email + n8n (Sesije 0–5) <!-- id:mvpsr -->

Završeno: 2026-05-01

FastAPI + Claude Haiku 4.5/Sonnet 4.6, lokalni RAG (sentence-transformers +
BM25 hibrid), 4 tool-a (`search_products`, `get_faq`, `check_availability`,
`escalate_to_human`), 3 kanala (widget, voice, email), n8n cloud email
automatizacija. 18 eval pitanja, README sa pitch sekcijom. Detalji:
`docs/archives/bitlab-mvp-plan.md` Sesije 0–5.

### Sesija 6 — n8n na lokalni hosting <!-- id:s6n8n -->

Završeno: 2026-05-03 (kod), čeka DNS odblok za prod

Migracija sa cloud + ngrok na lokalni Docker (subpath + Gmail OAuth,
`feature/n8n-deploy` branch, commit `d485b0a`). Ngrok uklonjen iz n8n JSON-a
+ `HOSTING.md`. Production DNS koji Rale treba da publikuje nije legao —
workaround se radi u `p1fix`.

### Sesija 7 — Quality polish (7.1, 7.2, 7.4, 7.6, 7.7) <!-- id:s7pol -->

Završeno: 2026-05-02

Smart product matching (7.1 — `category_terms.json`, scripts/build_category_terms.py),
CPU-only deps + brži startup od 60s na 2.7s (7.2 — lazy import + bg preload
+ ST<4 pin), prompt review (7.4 — 11 pravila + injection delimiter), security
backlog (7.6 — slowapi + CORS + size guards + contacts.py), code review (7.7 —
`docs/reviews/code-review.md`). S7.3 (STT fix) riješeno drugačije od plana —
Groq Whisper ostao primarni (`e9baa9c`); S7.5 (voice→email cycle) je u
`vord` Later. Detalji: `docs/archives/bitlab-mvp-plan.md` Sesija 7.

### Production-prep + dashboard (Sesija 8) <!-- id:prodp -->

Završeno: 2026-05-04

AI klasifikacija kategorija (`data/categories.json`, 30 kategorija — kasnije
prošireno na 89 u `livet`), Sonnet 4.6 kao default chat (Haiku izbačen zbog
typo halucinacija + lažne "nema laptopa"), email šablon sa mailto, graceful
API error handling, fine-grained logging dashboard (React 19 + Vite 8 +
Tailwind 4, port iz `playwright-router`-a — 9 stranica umjesto planiranih 6:
dodate Overview, Sessions, SessionDetail), voice UX redesign (fullscreen orb),
deploy artefakti (`scripts/deploy.sh`, `deploy/{bitlab-ai.service, nginx-site.conf,
README, RUNBOOK-prod, MANUAL-setup-domain}`). Detalji: `docs/plans/production-prep.md`
+ `docs/changes.md`.

### LIVE test + AI search hardening (2026-05-08) <!-- id:livet -->

Završeno: 2026-05-08

Backend + chat widget pušteni na webshop.bitlab.rs (voice privremeno hiddran
po `LIVE.md` Plan B, kasnije vraćen — Plan A ElevenLabs preskočen).
`feature/ai-search-brand-category-improvements` merge: 89 kategorija (vs 13),
90 brendova (`data/brend.json`), bidirectional prefix match, head-noun
fallback. Mobile responsive dashboard. Widget CSS leak iz host webshop-a
(`input:focus` override). Detalji: `LIVE.md` + `docs/features/ai-search-improvements.md`.

### Git konsolidacija + bitlab-standards adopcija (2026-05-15) <!-- id:bsgit -->

Završeno: 2026-05-15

LF line-endings enforcement (`.gitattributes`), feature branch
sinhronizacija (`feature/n8n-deploy`, `feature/openclaw-integration`),
uvođenje bitlab-standards u repo (`CLAUDE.md` @-import,
`STATUS.md` kreiranje, decisions u `docs/brainstorm/`). Commits
`d9d5c84..cd580fd`.
