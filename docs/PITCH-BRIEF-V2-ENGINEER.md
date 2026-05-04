# Pitch deck v2 — instrukcije za Claude Design (inženjerska publika)

> **Za:** Claude Design instanca koja ima pristup PowerPoint/Figma/Canva alatima
> **Cilj:** ažurirati postojeću prezentaciju (`public/assets/BitLab AI Asistent.pdf`)
> **Razlog:** trenutna v1 je marketing-orijentisana, publika je inženjer

---

## 0. Šta NEMOJ raditi (greške v1 verzije)

Trenutna prezentacija (`public/assets/BitLab AI Asistent.pdf`) je za business-decision-maker publiku. Stari `PITCH-BRIEF.md` ima sekciju "Šta NE pominjati" koja kaže ne pominji "Claude Haiku 4.5", "BM25", "cosine similarity". **Za inženjera obrni** — to su upravo riječi koje grade kredibilitet.

**NE radi:**
- Marketinške slogane ("Drugi pričaju o AI-u. Mi ga isporučujemo")
- Generic value-prop slajdove ("24/7 dostupnost", "smanjuje opterećenje tima")
- Skrivanje tehničkih odluka iza brendiranja
- Stat-grid sa apstraktnim brojkama tipa "94% accuracy" bez konteksta šta to mjeri

**RADI:**
- Pokaži arhitekturne odluke i **zašto** su odabrane (sa alternativama koje su odbačene)
- Pokaži konkretne bug-ove iz produkcije i kako su riješeni (ovo gradi credibility)
- ASCII / sequence dijagrami umjesto ikonica
- Brojeve sa kontekstom: "Sonnet 4.6 41/41 eval, Haiku 4.5 34/36 (typo halucinacije)"
- Otvoreno priznaj otvorena pitanja (Sesija 9 multi-provider eval, growth track)

---

## 1. Audience profile

**Inženjer.** Pretpostavlja se:
- Prati LLM ekosistem (zna razliku između modela, prompt engineering, RAG)
- Razumije Python/FastAPI, async, SQLAlchemy, REST/SSE
- Razumije React/TypeScript bar površno
- Postavlja pitanja o latency-ju, cost-u, schema migracijama, deploy strategiji
- Cijeni honesty oko trade-off-ova više nego polish

**Goal slajda:** "ovo je system koji bi i ja sam htio da pišem; razgovor sa autorom će biti tehnički koristan, ne marketing-y".

---

## 2. Šta je novo od v1 prezentacije

V1 deck (postojeći PDF) napisan je prije Sesije 8. Sve ovo nije bilo:

### A) Logging dashboard sa fine-grained tool call timeline

Zasebna React 19 + Vite 8 + TS aplikacija u `dashboard/`. 7 stranica. Najvažnije:
- **Sessions** — thread view razgovora (jedan red = jedna sesija klijent+AI), klik → cijela komunikacija turn-by-turn
- **RequestDetail** — za svaku poruku timeline svih tool calls-ova sa input JSON, output text, latency po koraku
- **Compare** — paralelan fan-out istog upita kroz 2+ modela (haiku ↔ sonnet)

To je glavni diferencijator — "ne gledamo AI kao black box, vidimo svaki tool call sa svim parametrima i timing-om".

Detalji: [`features/logging-dashboard.md`](./features/logging-dashboard.md), [`features/sessions.md`](./features/sessions.md), [`features/compare.md`](./features/compare.md)

### B) AI klasifikacija namjere — kategorijski filter sa eval-om

`data/categories.json` sa top 30 kategorija (81.5% kataloga). Claude vidi listu kao `enum` u tool schema-i + tekstualno u tool description-u, **single API poziv** rješava i klasifikaciju i tool decision. Hard filter u `rag.py` drastično smanjuje accessory šum ("torba za laptop" izlazi van pretrage za "laptop").

Eval: 41 realan upit, **100%** top-1 accuracy sa Sonnet-om (uključujući 5 typo cases).

Detalji: [`features/ai-classification.md`](./features/ai-classification.md)

### C) Modelska odluka — Sonnet 4.6 (Haiku izbačen)

**Hard-won lesson iz live demo-a**, ozbiljan engineering moment:

Haiku 4.5 je u produkciji:
1. Tražio pojašnjenje za "Imate li **lapatovoe**" (typo za laptop) umjesto da pozove search
2. Sledeći turn: rekao "trenutno nemamo dostupnih laptopa u katalogu" iako catalog ima 50

Ovo nije promptable bug — Haiku ne sluša pravila pouzdano za production-grade B2C. Sonnet 4.6 sa istim promptom: 41/41 eval, plus 6/6 typo regression testova.

Trade-off: Sonnet ~3× skuplji input/output, ~2× sporiji. Za naš volumen (~1.000 chat upita/mj) razlika je ~$1.20/mj — prihvatljivo za pouzdanost.

Detalji: [`plans/model-eval.md`](./plans/model-eval.md) — Sesija 9 ovaj tjedan testira GPT-4o-mini, Llama 3.x, DeepSeek-V3 na istom eval setu, ekonomska odluka kraj sedmice.

### D) Defensive layeri iz live demo bug-ova

Niz produkcionih bug-ova zatvorenih regression testovima:

| Bug | Fix |
|---|---|
| TTS čita "1.936 KM" kao "jedna marka" | `_normalize_for_tts()` heuristika za BCS format (tačka kao separator hiljada) |
| `<voice>` tagovi cure u chat UI | `_strip_voice_tags()` u backendu + widget defensive layer |
| Markdown tabele se prikazuju kao tekst sa `\| crta` | `_strip_markdown_tables()` |
| Slika ne učitava za 7.2% kataloga | Audit script + `image_url=None` filter u `rag.py` |
| Halucinacija "Prodajni tim je obaviješten" iako ništa nije slano | SMTP integracija u `escalate_to_human` ili honest fallback |
| 500 Internal Server Error kad Anthropic kredit potrošen | Graceful 400/429/network handler sa friendly fallback porukom |

Test coverage: 62 unit/integration + 41 eval + 10 Node testova. Sve regression testovi spriječavaju ponavljanje.

### E) Voice UX redesign

Voice modal: fullscreen orb (160px centriran) na otvaranje → animirano skupljanje u kompaktan header (25%) kad stigne prvi rezultat, body (75%) sa product cards. Thinking sound: procedural Web Audio "tu-nu-nu" pattern (110/165/247 Hz + sub-oktave).

### F) Deploy pattern (symlink releases, server konvencije)

Pattern A iz `DEPLOY_GUIDE.md` (Ivanov master) — `releases/<timestamp>/`, `shared/var/`, atomic symlink switch, systemd unit, nginx pod `/admin/`. 8 komandi cheatsheet u `DEPLOY.md`.

---

## 3. Slajd-by-slajd preporuke za v2

> Korisnik (klijent na pitch sastanku) je inženjer. Vrijeme: ~10 minuta.
> **Strategija:** smanjiti broj slajdova, dublji sadržaj po slajdu.

### Slajd 1 — Cover

Naslov: **BitLab AI Asistent**
Subtitle: *Production system, ne demo* (zadržati)
Plus mali tehnički sub-subtitle: *4 kanala · Sonnet 4.6 · fine-grained logging dashboard · symlink deploy*

### Slajd 2 — Šta je sistem (high-level)

ASCII dijagram (NE ikonice). Predlog:

```
┌──────────────────────────────────────────────────────────┐
│  FastAPI backend (Python 3.11+, async)                   │
│  4 endpointa public · 7 endpointa /api/dashboard/*       │
│                                                          │
│  Agent loop (Claude tool use, max 5 iter):               │
│   search_products(query, category_id, max_price, top_k)  │
│   get_faq(topic) · check_availability(sifra)             │
│   escalate_to_human(reason, summary)                     │
└──────────────────────────────────────────────────────────┘
       ▲              ▲             ▲              ▲
   ┌───┘              │             │              │
┌──────────┐ ┌────────────────┐ ┌──────────┐ ┌──────────────┐
│ Widget   │ │ Voice mode     │ │ Email    │ │ Dashboard    │
│ widget.js│ │ (fullscreen→   │ │ n8n IMAP │ │ React+Vite   │
│ 1 file,  │ │  compact UX)   │ │ →SMTP    │ │ /admin/      │
│ embed    │ │ STT chain:     │ │ trigger  │ │ Sessions tab │
│          │ │ Groq→Azure→    │ │          │ │ thread view  │
│          │ │ faster-whisper │ │          │ │              │
└──────────┘ └────────────────┘ └──────────┘ └──────────────┘
```

### Slajd 3 — Sessions tab screenshot (HERO slajd)

Screenshot `/admin/sessions` tabele + screenshot `/admin/sessions/:id` turn-by-turn detail. Naslov: **"Pratimo svaki tool call AI agenta"**.

Bullets ispod:
- Thread view — jedan red = jedan razgovor (ne pojedinačne poruke)
- Klik → User/Assistant bubble pattern, tool calls expand između turn-ova
- Latency, tokens, cost per session i per turn
- Polling 5s, fresh-row highlight

Ovo je **glavni diferencijator vs konkurencija**. Niko drugi ne pravi ovakvu observability za chat asistente u BCS regiji.

### Slajd 4 — AI klasifikacija — odluka i tradeoffi

Naslov: **"Single-call klasifikacija + hard category filter"**

Tri sloja klasifikacije (sa kratkim opisom):
1. **AI klasifikacija namjere** — Claude bira `category_id` u istom pozivu kao tool decision (single round-trip, ne classify→search dva poziva)
2. **Build-time prefix** (`category_terms.json`) — semantičko obogaćenje search_text-a
3. **Search-time soft boost** — fallback kad AI ne pošalje category_id

Eval brojevi (mjereno):
- 41/41 = **100%** sa Sonnet-om
- 34/36 = 94.4% sa Haiku-om — typo case-ovi pucaju
- 5 dedikovanih typo regression testova

### Slajd 5 — Hard-won lesson: Haiku vs Sonnet

Naslov: **"Why we don't use Haiku 4.5 anymore"**

Konkretni bug iz live demo-a:
```
User: "Imate li lapatovoe"
Haiku: [Tool call NOT made — asks for clarification instead]
        "Možete li pojasniti? Mislite li na laptop ili lapto kao dio uređaja?"

User: "Laptop"
Haiku: "Nažalost, trenutno nemamo dostupnih laptopa u katalogu."
        ↑↑ HALUCINACIJA — catalog ima 50 laptopa u cat 98 ↑↑
```

Sonnet 4.6 sa identičnim promptom:
```
User: "Imate li lapatovoe"
Sonnet: [search_products(query="laptop", category_id="98")]
        → vraća 5 laptopa sa cijenama, slikama, linkovima
```

Trade-off: Sonnet ~3× input cost, 2× sporiji. Za naš volume razlika je $1.20/mj. **Pouzdanost > cijena** za production B2C.

Sledeći korak: Sesija 9 ovaj tjedan testira GPT-4o-mini, Llama 3.3 70B, DeepSeek-V3 na istom eval setu. Ekonomska odluka kraj sedmice ako je bilo koji ≥99% accuracy + 0% halucinacija.

### Slajd 6 — Defensive layeri (production hardening)

Naslov: **"6 production bug-ova, 6 regression testova"**

Tabela bug → fix → test:

| Demo bug | Backend fix | Test |
|---|---|---|
| TTS "1.936 KM" → "jedna marka" | `_normalize_for_tts()` BCS hiljada heuristika | 11 cases |
| `<voice>` tagovi cure u chat | `_strip_voice_tags()` | 7 testova |
| Markdown tabele kao text | `_strip_markdown_tables()` | 4 testa |
| Slika 7.2% missing iz CDN-a | `audit_missing_images.py` + `image_url=None` filter | 5 testova |
| "Tim je obaviješten" laž | SMTP integracija ili honest fallback | manualno |
| 500 kad kredit potrošen | Graceful 400/429/network handler | manualno |

Ukupno: **62 unit/integration + 41 eval + 10 Node** testova.

### Slajd 7 — Compare panel (live A/B testiranje)

Screenshot `/admin/compare`. Naslov: **"Empirijski biramo modele"**

Mehanika:
- Paste prompt
- Selektuj 2+ modela
- `asyncio.gather` paralelni fan-out
- Side-by-side rezultati: latency, tokens, cost, **tool calls per model**

Primjer realne kompariranja iz Stats tab-a:
```
"imate li tastaturu" — chat channel
  Haiku  6.5s  ↓9467 ↑215  $0.0105  1 tool call
  Sonnet 17.0s ↓13834 ↑257 $0.0454  2 tool calls (search + retry)
```

Ova infrastruktura nam omogućava da sutra testiramo GPT-4o-mini bez ikakvog code change-a — samo dodaj u `model_registry`.

### Slajd 8 — Stack i deploy strategija

Naslov: **"Stack i operativni model"**

Backend:
- FastAPI + Python 3.11 (async lifespan, async SQLAlchemy)
- SQLite (`requests` + `tool_calls` tabele, `Request.session_id` indexed)
- Claude Sonnet 4.6 default; model registry za override
- Embeddings: sentence-transformers MiniLM-L12-v2, 384 dim, BCS multilingual, lokalno (0 API trošak)
- TTS chain: Azure Speech → edge-tts fallback
- STT chain: Groq Whisper → Azure → faster-whisper

Frontend:
- React 19 + Vite 8 + TypeScript 6 + Tailwind 4
- 7 stranica + axios sa Bearer interceptor + TanStack Query polling
- Build: 347KB JS / 108KB gzipped, statičan dist (nginx serves)

Deploy:
- Pattern A: `releases/<timestamp>/` + atomic symlink → `current/`
- systemd unit (memory limit 1.5GB, restart on-failure)
- nginx `/admin/` location → static dist, `/api/` → proxy 127.0.0.1:8000
- 8 komandi za re-deploy (vidi `DEPLOY.md`)

### Slajd 9 — Open questions (otvoren završetak)

Naslov: **"Šta još nije zatvoreno"**

Iskreno reci publici:
- **Multi-provider eval** — Sesija 9 ovaj tjedan, GPT-4o-mini / Llama / DeepSeek vs Claude
- **Server-side install** — dokumentacija gotova, fizički deploy na `aiasistent-prod` čeka
- **Webshop CSP** — treba provjeriti da `<script src="ai.bitlab.rs/widget.js">` prolazi
- **Email kanal session grouping** — trenutno svaki email novi session, treba `session_id = sha256(sender)`
- **Per-token streaming** — trenutni MVP nema, korisnik vidi "Razmišljam..." dok cijeli odgovor ne stigne
- **Backup strategija** — SQLite cron `.backup` pravilo nije postavljeno
- **Cost guard** — nema rate limit per IP, nema budget alert

Inženjer cijeni honesty oko otvorenih pitanja više nego false completeness.

### Slajd 10 — Roadmap (Sesije 9 + 10 paralelno)

Sledeća dva tjedna:

**Sesija 9 — Multi-provider eval (sedmica 2026-W19):**
- Anthropic Sonnet/Haiku/Opus, OpenAI GPT-4o-mini/4.1-mini/4o, Meta Llama 3.3 70B / 3.1 8B (Groq), DeepSeek-V3
- Tehnički prag: ≥99% accuracy + 0% halucinacija
- Subjektivni prag: 5-pt Likert ≥4.0/5.0 po kategoriji (15 scenarija)
- Ekonomska odluka po podacima kraj sedmice

**Sesija 10 — Growth (kontinuirano od W19):**
- Tehnički + kompetitivni SEO audit (Comtrade, ADM, Kim Tec, Nest, WinWin)
- Content production (kategorijski vodiči, FAQ how-to)
- Link building automatizacija (lokalni katalozi, partnerski outreach, digital PR)
- Paid ads automatizacija (Google Shopping feed iz `all-products.json`)
- AI asistent kao growth tool: email capture, newsletter, cart abandonment recovery, review request automation, log insights → content backlog

KPI 90 dana: organic +50%, referring domains +20.

### Slajd 11 — Q&A / Kontakt

Ostavi praznu, samo: **"Pitanja?"** + kontakt info (ime, email, GitHub repo URL ako je javan).

Inženjer će postaviti specifična pitanja — bolje da imamo prostor za razgovor nego pre-canned slajd.

---

## 4. Stilske napomene za engineering pitch

### Tipografija
- **JetBrains Mono za sve cifre, ID-jeve, code snippets, file paths** (kako u dashboard-u radi)
- Inter ili sistem sans-serif za prose
- Hierarchy: 22px H1, 16-18px za stat numbers (mono), 13px body, 10px section labels (uppercase, mono, letterspacing 0.08em)

### Boje
- BitLab orange `#fb6d3b` ostaje primarni accent — ali samo za CTA/branded elements
- **Dark theme** za code/terminal slajdove (kao u dashboard-u): `#0b0d10` background, `#7dd3fc` cyan accent za code highlights, `#4ade80` zeleno za "ok/done", `#f87171` crveno za "error/halucinacija"
- Dijagrami: minimal, monoizam, ASCII gdje god moguće

### Slajdovi koji moraju imati screenshot
- Slajd 3 (Sessions tab) — to je hero, MORA biti realna slika
- Slajd 5 (Haiku bug) — terminal-style sa pravim quote-ovima
- Slajd 6 (Compare) — screenshot side-by-side rezultata
- Slajd 7 (deploy pattern) — možda ASCII tree `releases/`, `shared/`, `current →`

### Šta IZBJEGAVATI
- Stock fotografije (mozgovi, robot ruke, tech grids)
- Generic "AI for business" slajdovi
- Slogani sa znakovima uskličnika
- Brojeve bez konteksta (npr. "94%" ali ne kažeš na čemu)

---

## 5. Reference za Claude Design

Kompletna tehnička dokumentacija je u `docs/`:
- [`docs/README.md`](./README.md) — index svih fajlova
- [`docs/architecture.md`](./architecture.md) — high-level overview, ASCII dijagram, struktura
- [`docs/features/sessions.md`](./features/sessions.md) — Sessions feature za slajd 3
- [`docs/features/ai-classification.md`](./features/ai-classification.md) — kategorije za slajd 4
- [`docs/features/logging-dashboard.md`](./features/logging-dashboard.md) — dashboard pregled
- [`docs/features/compare.md`](./features/compare.md) — Compare za slajd 7
- [`docs/plans/model-eval.md`](./plans/model-eval.md) — Sesija 9 detalji za slajd 10
- [`docs/plans/growth.md`](./plans/growth.md) — Sesija 10 detalji za slajd 10
- [`docs/changes.md`](./changes.md) — diff vs main, lista svega što je urađeno

Stari pitch brief: [`../public/assets/PITCH-BRIEF.md`](../public/assets/PITCH-BRIEF.md) — koristan za **brand boje, BitLab kontekst, tehničku biografiju klijenta**, ali NE za stil/ton (taj brief je business-oriented, ne engineering).

Stari PDF: [`../public/assets/BitLab AI Asistent.pdf`](../public/assets/BitLab AI Asistent.pdf) — **referenca za vizuelnu konzistentnost** (boje, layout grid), NE za sadržaj (sadržaj zamjenjujemo kako je opisano gore).

---

## 6. Format isporuke

- **PowerPoint .pptx** preferred — Ivan može da edituje slajdove finalno
- Plus PDF export za distribuciju
- Slajdovi 16:9, 1920×1080 (4K opciono za hero slajdove)

---

## 7. Pitanja za Ivana ako Claude Design nije siguran

Prije nego krene, Claude Design treba da pita:
1. Koliko vremena je za pitch? (10 min / 20 min / 45 min — utiče na broj slajdova i dubinu)
2. Da li je publika 1 osoba ili više? (1 inženjer = razgovor; tim = strukturirana prezentacija)
3. Da li klijent zna kontekst projekta ili krećemo od nule?
4. Postoji li specifičan tehnički detalj koji klijent mu je rekao da očekuje da bude pokriven?
5. Live demo planiran ili samo slajdovi?
