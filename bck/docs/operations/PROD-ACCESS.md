# BitLab AI Asistent

AI prodajni asistent za **webshop.bitlab.rs** — chat widget + voice mode + email auto-reply, sa logging dashboard-om za nadzor.

Production server: `aiasistent.bitlab.rs` (Hetzner VPS), release-symlink deploy + systemd + nginx + Let's Encrypt.

---

## Linkovi

| Šta | URL |
|------|-----|
| **Chat widget** | https://aiasistent.bitlab.rs |
| **Dashboard (logovi, sesije, stats)** | https://aiasistent.bitlab.rs/admin/ |
| **Health check** | https://aiasistent.bitlab.rs/healthz |
| **Prezentacija (PDF)** | [Engineering Pitch v2](https://aiasistent.bitlab.rs/public/assets/BitLab%20AI%20Asistent%20%E2%80%94%20Engineering%20Pitch%20v2.pdf) |

### Pristup dashboard-u

Dashboard je iza HTTP Basic Auth-a.

| | |
|---|---|
| URL | https://aiasistent.bitlab.rs/admin/ |
| Username | `bitlab` |
| Password | _podijelimo zasebnim kanalom_ |

Browser pamti credentials za sesiju. API ključ za logove se auto-učitava — ne treba ništa kucati u Settings.

---

## Šta vidiš u dashboard-u

- **Overview** — ukupne statistike, troškovi, broj zahtjeva po danu, posljednje sesije
- **Sessions** — cijeli razgovori po session_id (chat / voice / email kanali)
- **Live** — live stream zahtjeva u realnom vremenu
- **History** — kompletna lista pojedinačnih request-ova sa tokenima, latencijom, cijenom
- **Compare** — A/B testiranje različitih modela na istom promptu
- **Stats** — agregat po modelu/kanalu/adapteru

---

## Tech stack

- **Backend:** FastAPI (Python 3.13, uvicorn)
- **LLM:** Claude Sonnet 4.6 za chat i email
- **STT:** Groq Whisper-large-v3-turbo (BCS-jezici)
- **TTS:** Edge TTS
- **Embeddings:** sentence-transformers, ~5300 proizvoda u indeksu (BM25 hybrid)
- **Storage:** SQLite (dashboard logs) + JSON (katalog, kategorije, FAQ)
- **Frontend:** Vite + React 19 + TanStack Query (dashboard SPA)

Detaljnije u Engineering Pitch v2 PDF-u (link iznad).
