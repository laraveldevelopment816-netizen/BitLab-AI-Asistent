# README-STANDARD — bitlab-ai-asistent

Standardizovani README za pokretanje projekta na drugom računaru. Tri sekcije,
skenirajući format: copy-paste komande u fenced blokovima.

---

## 1. O čemu je projekat

`bitlab-ai-asistent` je **multi-channel AI prodajni asistent** za
`webshop.bitlab.rs`. Četiri kanala dijele istu bazu znanja (5.278 proizvoda
+ FAQ):

- **Chat widget** — embed na webshop kroz `<script>` tag
- **Voice mode** — STT (Groq Whisper) → agent → TTS (Azure neural)
- **Email auto-reply** — n8n IMAP trigger → `/api/email`
- **Dashboard** — `/admin/` sa fine-grained tool call timeline-om

Stack: **FastAPI + Python 3.11+**, LLM **Claude Sonnet 4.6**, storage SQLite
+ SQLAlchemy async, dashboard **React 19 + Vite 8 + TS**, lokalni embedding
preko sentence-transformers MiniLM-L12-v2.

---

## 2. Kako se pokreće

Lokalno: Python venv + pnpm dashboard. Trebaš Python 3.11+ i pnpm.

```bash
# 1. Klonira j repo
git clone https://github.com/laraveldevelopment816-netizen/BitLab-AI-Asistent.git
cd BitLab-AI-Asistent

# 2. Venv + deps (CPU-only torch wheel)
python3 -m venv .venv && source .venv/bin/activate
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu

# 3. .env (popuni ANTHROPIC_API_KEY i DASHBOARD_API_KEY)
cp .env.example .env
nano .env

# 4. Bootstrap baze (jednokratno, ~5min za embed-e)
python scripts/embed_products.py
python scripts/build_categories.py
python scripts/init_db.py

# 5. Backend (terminal 1)
uvicorn app.main:app --reload
```

Dashboard (drugi terminal):

```bash
cd dashboard && pnpm install && pnpm dev
```

Otvori `http://localhost:8000` (chat widget) i `http://localhost:5173/admin/`
(dashboard).

Testovi:

```bash
pytest                            # unit
pytest -m anthropic_api           # integration sa pravim API-jem (~$0.02/test)
```

---

## 3. Šta i kako radi

| Komponenta | Tehnologija | Port / putanja |
|---|---|---|
| Backend API | FastAPI + uvicorn | `:8000` |
| Dashboard | React 19 + Vite | `:5173` |
| Baza | SQLite (async) | `data/*.db` |
| Embeddings | sentence-transformers (lokalno) | `data/embeddings/` |
| LLM | Claude Sonnet 4.6 (Anthropic API) | preko `ANTHROPIC_API_KEY` |
| Voice STT | Groq Whisper | preko `GROQ_API_KEY` |
| Voice TTS | Azure Speech (neural), edge-tts fallback | preko `AZURE_SPEECH_KEY` |

Endpoint-i: `/api/chat`, `/api/email`, `/api/voice`, `/admin/`. Health:
`GET /healthz` → 200. Detalji + dijagrami: [`docs/architecture.md`](docs/architecture.md)
i [`docs/getting-started.md`](docs/getting-started.md).

Deploy: staging na `staging.aiasistent.bitlab.rs`, prod na `aiasistent.bitlab.rs`
(systemd `aiasistent-prod` / `aiasistent-staging`). Server-side komande:
[`docs/operations/DEPLOY.md`](docs/operations/DEPLOY.md).
