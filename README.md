# BitLab AI Asistent

Multi-channel AI prodajni asistent za **webshop.bitlab.rs** sa fine-grained logging dashboard-om.

Četiri kanala dijele istu bazu znanja (5.278 proizvoda + FAQ):
- 💬 **Chat widget** — embed na webshop kroz `<script>` tag
- 🎙️ **Voice mode** — STT (Groq Whisper) → agent → TTS (Azure neural)
- 📧 **Email auto-reply** — n8n IMAP trigger → `/api/email`
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

Često traženo:

| | |
|---|---|
| Pokretanje lokalno | [`docs/getting-started.md`](./docs/getting-started.md) |
| Stack i arhitektura | [`docs/architecture.md`](./docs/architecture.md) |
| Kako radi voice mode | [`docs/features/voice-mode.md`](./docs/features/voice-mode.md) |
| Kako radi dashboard | [`docs/features/logging-dashboard.md`](./docs/features/logging-dashboard.md) |
| AI klasifikacija (kategorije) | [`docs/features/ai-classification.md`](./docs/features/ai-classification.md) |
| Compare panel (haiku ↔ sonnet) | [`docs/features/compare.md`](./docs/features/compare.md) |
| Česti problemi | [`docs/operations/troubleshooting.md`](./docs/operations/troubleshooting.md) |
| Troškovi | [`docs/operations/costs.md`](./docs/operations/costs.md) |
| Razvojni workflow + testovi | [`docs/development.md`](./docs/development.md) |

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

## Kontakt

**BitLab d.o.o.** · Jevrejska 37, 78000 Banja Luka  
prodaja@bitlab.rs · 066 516 174 · webshop.bitlab.rs  
JIB: 4403711250001
