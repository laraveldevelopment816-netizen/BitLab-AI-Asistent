# Arhitektura

## High-level diagram

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
│ widget.js│ │ (orb→header,   │ │ IMAP→/email  │ │ React+Vite+TS  │
│          │ │  body cards)   │ │ →SMTP reply  │ │ /admin/        │
└──────────┘ └────────────────┘ └──────────────┘ └────────────────┘
```

## Stack

| Sloj | Tehnologija | Zašto |
|---|---|---|
| Backend | **FastAPI** (Python 3.11+, async) | nativno tool use, lifespan, async SQLAlchemy |
| LLM | **Claude Sonnet 4.6** (chat + voice + email) | discipline za production B2C (vidi [model-eval](./plans/model-eval.md)) |
| Embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | lokalno, BCS, 0 API trošak |
| Vector search | numpy cosine + rank-bm25 hibrid (0.6/0.4) | 5.278 vektora trivijalno in-memory |
| TTS | Azure Speech → edge-tts fallback | bs/hr/sr neural glasovi |
| STT | Groq Whisper → Azure → faster-whisper fallback | Whisper-large-v3 najbolji za bs/hr/sr |
| Storage | SQLite + SQLAlchemy async (`var/bitlab.db`) | requests + tool_calls tabele |
| Dashboard | React 19 + Vite 8 + TS + Tailwind 4 | port iz playwright-router |
| Email automatizacija | n8n Docker (lokalno) | IMAP trigger → /api/email |

## Knowledge base + storage

```
data/products.index.npz     5.278 vektora, 384 dim
data/products.meta.json     meta (ime, cijena, kolicina, URL, sifra)
data/categories.json        top 30 kategorija sa labelama
data/category_terms.json    build-time prefix + soft-boost terms
data/missing_images.json    audit output — koje slike fale na CDN-u
data/faq.md                 ručno kurirane sekcije
var/bitlab.db               SQLite — requests + tool_calls
                            (Request.session_id grupiše razgovor; preživi releaseve)
```

## Struktura projekta

```
bitlab-ai-asistent/
├── app/
│   ├── main.py            FastAPI: /api/chat, /email, /tts, /stt, /healthz
│   ├── agent.py           Claude tool-use loop, vraća _trace dict za logging
│   ├── tools.py           4 tool-a: schema + handleri + dispatcher
│   ├── rag.py             Hibrid: BM25 + vektor + hard category filter
│   ├── faq.py             FAQ keyword retrieval
│   ├── system_prompts.py  3 prompta: chat / voice / email
│   ├── email_poller.py    IMAP fallback (rezerva za n8n)
│   ├── config.py          Pydantic Settings, .env loader
│   ├── server/
│   │   └── dashboard.py   /api/dashboard/* — Bearer auth + compare
│   └── storage/
│       ├── db.py          async SQLAlchemy engine + sessionmaker
│       ├── models.py      Request + ToolCall (FK)
│       └── repo.py        insert + get helper-i
├── dashboard/             React 19 + Vite 8 + TS — 6 stranica
├── deploy/                bitlab-ai.service + nginx-site.conf
├── scripts/
│   ├── embed_products.py  generiše products.index.npz (jednokratno)
│   ├── build_categories.py top 30 kategorija sa labelama
│   ├── init_db.py         kreira requests + tool_calls schema
│   ├── audit_missing_images.py  paralelni HEAD check za broken slike
│   ├── deploy.sh          install/update/rebuild/restart
│   └── smoke_test.py      4 chat upita end-to-end
├── evals/
│   ├── category_eval.json + run_categories.py   41 upit, 100% baseline
│   ├── run_format.py                            mjeri raw Claude output
│   └── test_questions.json + run.py             originalni eval set
├── tests/                 pytest + Node renderer testovi
├── public/
│   ├── widget.html, widget.js, voice.html
└── docs/                  ova dokumentacija
```

## Data flow — chat poruka

```
korisnik kuca "imate li gaming mis"
  │
  ▼
widget.js POST /api/chat {message, history, channel}
  │
  ▼
agent.py run_agent() — Claude API poziv sa system prompt + tools
  │
  ▼ (Claude bira tool i parametre)
search_products(query="gaming miš", category_id="277", top_k=5)
  │
  ▼ (rag.py)
embedding cosine + BM25 fusion + hard filter cat=277
  │
  ▼ (Claude formatira reply iz tool result-a)
reply: "Imate 5 miševa: ..." sa product cards
  │
  ▼ (defensive layer)
_strip_voice_tags + _strip_horizontal_rules + _strip_markdown_tables
  │
  ▼ (paralelno)
   ├─→ widget.js renderMarkdown → product cards UI
   └─→ async _persist_trace → SQLite (visible u /admin/live u 5s)
```

Detalji po feature:
- Chat widget: [`features/chat-widget.md`](./features/chat-widget.md)
- Voice mode: [`features/voice-mode.md`](./features/voice-mode.md)
- AI klasifikacija + RAG: [`features/ai-classification.md`](./features/ai-classification.md)
- Kategorijski routing + parent expansion (ASCII flow): [`features/category-routing.md`](./features/category-routing.md)
- Logging dashboard: [`features/logging-dashboard.md`](./features/logging-dashboard.md)
