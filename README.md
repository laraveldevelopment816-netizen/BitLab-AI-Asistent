# BitLab AI Asistent

## Git workflow

```
   feature/*
       │
       ▼  PR + review
   ┌──────────┐
   │ staging  │ ──── auto deploy ───▶ staging.aiasistent.bitlab.rs
   └──────────┘
       │
       │  git merge staging   ◀── ⚠️ KRITIČNO PRIJE PROD DEPLOY-A
       ▼
   ┌──────────┐
   │   main   │ ──── manual deploy ──▶ aiasistent.bitlab.rs
   └──────────┘
```

**Branchevi:**
- `staging` — aktivan razvoj, sve PR-ovi se mergaju ovdje, auto-deploy na staging server
- `main` — samo prod-spremno; merge **isključivo** iz staging-a; manual deploy na prod
- `feature/*` — kratkotrajne grane, brišu se nakon merge-a u staging

**Backmerge poslije svakog PR-a staging → main:** odmah nakon GitHub merge-a pokreni `git checkout staging && git pull origin main && git push origin staging` — donosi merge commit nazad u staging i drži grane u sync-u za sledeći ciklus.

**OBAVEZAN pre-prod check** (pokreni prije svakog `setup-domain` ili `release` na prodi):

```bash
git fetch origin
git log origin/main..origin/staging --oneline
```

Ako lista nije prazna → **STOP**. Mergaj staging u main pa nastavi:

```bash
git checkout main
git merge staging
git push origin main
```

**Incident 2026-05-06:** prod aiasistent-a kloniran sa main koji nije imao mergovan staging — `dashboard/` folder nije postojao u main-u (pet commit-ova nedostajalo), `build_dashboard` skipovan, prod bez UI-ja. Pravilo gore je odgovor.

---

Multi-channel AI prodajni asistent za **webshop.bitlab.rs** sa fine-grained logging dashboard-om.

Četiri kanala dijele istu bazu znanja (5.278 proizvoda + FAQ):
- 💬 **Chat widget** — embed na webshop kroz `<script>` tag
- 🎙️ **Voice mode** — STT (Groq Whisper) → agent → TTS (Azure neural)
- 📧 **Email auto-reply** — n8n Gmail trigger → `/api/email`
- 📊 **Dashboard** — `/admin/` sa fine-grained tool call timeline-om

Backend: **FastAPI + Python 3.11+** · LLM: **Claude Sonnet 4.6** · Storage: **SQLite + SQLAlchemy async** · Dashboard: **React 19 + Vite 8 + TS** · Embed: **sentence-transformers MiniLM-L12-v2** (lokalno, BCS).

---

## Brzi start

```bash
git clone https://github.com/laraveldevelopment816-netizen/BitLab-AI-Asistent.git
cd BitLab-AI-Asistent
python3 -m venv .venv && source .venv/bin/activate
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu
cp .env.example .env && nano .env   # popuni ANTHROPIC_API_KEY, DASHBOARD_API_KEY
python scripts/embed_products.py    # ~5min, jednokratno
python scripts/build_categories.py
python scripts/init_db.py
uvicorn app.main:app --reload
```

Dashboard (drugi terminal):
```bash
cd dashboard && pnpm install && pnpm dev
```

Otvori http://localhost:8000 (chat) i http://localhost:5173/admin/ (dashboard).

Detalji: **[`docs/getting-started.md`](./docs/getting-started.md)**

---

## Dokumentacija

Sve detalje, dijagrame i feature-by-feature objašnjenja drži **[`docs/`](./docs/)** sa **[`docs/README.md`](./docs/README.md)** kao indexom.

Često traženo (najnovije na vrhu):

| Datum | Tema | Link |
|---|---|---|
| 2026-05-08 | **AI search: brendovi + proširene kategorije** (NOVO) | [`docs/features/ai-search-improvements.md`](./docs/features/ai-search-improvements.md) |
| 2026-05-04 | Pokretanje lokalno | [`docs/getting-started.md`](./docs/getting-started.md) |
| 2026-05-04 | Stack i arhitektura | [`docs/architecture.md`](./docs/architecture.md) |
| 2026-05-04 | Kako radi voice mode | [`docs/features/voice-mode.md`](./docs/features/voice-mode.md) |
| 2026-05-04 | Kako radi dashboard | [`docs/features/logging-dashboard.md`](./docs/features/logging-dashboard.md) |
| 2026-05-04 | AI klasifikacija (kategorije) | [`docs/features/ai-classification.md`](./docs/features/ai-classification.md) |
| 2026-05-04 | Compare panel (haiku ↔ sonnet) | [`docs/features/compare.md`](./docs/features/compare.md) |
| 2026-05-04 | Česti problemi | [`docs/operations/troubleshooting.md`](./docs/operations/troubleshooting.md) |
| 2026-05-04 | Troškovi | [`docs/operations/costs.md`](./docs/operations/costs.md) |
| 2026-05-04 | Razvojni workflow + testovi | [`docs/development.md`](./docs/development.md) |

> Kompletan indeks svih dokumenata: [`docs/README.md`](./docs/README.md).

---

## Aktivne rezolucije

| # | Plan | Šta radi |
|---|---|---|
| 8 | [`docs/plans/production-prep.md`](./docs/plans/production-prep.md) | Production-readiness (završeno, čeka server-side install) |
| 9 | [`docs/plans/model-eval.md`](./docs/plans/model-eval.md) | Multi-provider eval — ekonomska odluka kraj sedmice 2026-W19 |
| 10 | [`docs/plans/growth.md`](./docs/plans/growth.md) | SEO + content + link building + AI growth tool |

Diff vs `main` (28 commit-ova): [`docs/changes.md`](./docs/changes.md)

---

## Deploy

Server-side: **[`DEPLOY.md`](./DEPLOY.md)** (8 komandi, copy-paste).
Server konvencije (Pattern A, port mapa): [`docs/operations/server-conventions.md`](./docs/operations/server-conventions.md).

Trenutni deploy target: `aiasistent-prod` na `aiasistent.bitlab.rs`, `aiasistent-staging` na `staging.aiasistent.bitlab.rs`.

---

## n8n automatizacija

n8n hostuje server-side workflow-e koji proširuju asistent (native npm + systemd, nije Docker — vidi [`docs/operations/n8n-setup.md`](./docs/operations/n8n-setup.md)).

| Environment | URL (trenutno aktivan, subpath) | Port | Final URL (kad DNS bude live) |
|---|---|---|---|
| Staging | https://staging.aiasistent.bitlab.rs/n8n/ | 8031 | https://n8n-staging.bitlab.rs |
| Production | https://aiasistent.bitlab.rs/n8n/ | 8030 | https://n8n.bitlab.rs |

Aktivni / planirani workflow-i:
- **Email auto-reply** (`n8n/email-autoreply.json`) — Gmail trigger → `/api/email` → AI reply. Filtrira po ključnim riječima u subject-u/snippet-u (upit, ponuda, cijen, dostava, garancija, …).
- **Sales workflow za povećanje prodaje na webshop-u** — počev od **idu sedmice (2026-W20, 11.05.2026.)**. Detalji se dogovaraju; vjerovatno lead nurturing, abandoned-cart, follow-up sekvence.

URL na koji workflow zove FastAPI app dolazi iz `AI_ASSISTANT_URL` env vara u systemd unit-u (`deploy/n8n-staging.service` → `http://127.0.0.1:8001`, `deploy/n8n-prod.service` → `http://127.0.0.1:8000`), pa se isti workflow JSON koristi na oba environmenta.

Trenutno stanje, plan nastavka, workaround bez DNS-a — sve u [`docs/operations/n8n-odluka.md`](./docs/operations/n8n-odluka.md).

---

## Kontakt

**BitLab d.o.o.** · Jevrejska 37, 78000 Banja Luka  
prodaja@bitlab.rs · 066 516 174 · webshop.bitlab.rs  
JIB: 4403711250001
