# Getting started

Cilj: za **5–10 minuta** imati pokrenutu aplikaciju lokalno i znati gdje šta da diraš.

## 1. Preduslovi

| Alat | Verzija | Provjera |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| Node.js | **22 LTS** | `node -v` |
| pnpm | 8+ | `pnpm -v` |

> **WSL2 napomena:** drži `.venv` izvan `/mnt/c` — Python import preko 9p protokola je 5–10× sporiji. Kod može ostati gdje je, samo venv u `~/.venvs/bitlab`.
>
> Node 22 install (ako fali ili imaš v20):
> ```bash
> sudo rm -f /etc/apt/sources.list.d/nodesource.list /etc/apt/keyrings/nodesource.gpg
> curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
> sudo apt-get install -y nodejs && sudo npm i -g pnpm
> ```

## 2. Klon + venv

```bash
git clone https://github.com/laraveldevelopment816-netizen/BitLab-AI-Asistent.git
cd BitLab-AI-Asistent
python3 -m venv .venv && source .venv/bin/activate
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu
```

CPU torch je obavezan flag — CUDA wheel je 1.2 GB, CPU 200 MB.

## 3. `.env`

```bash
cp .env.example .env
nano .env
```

**Obavezno:**
- `ANTHROPIC_API_KEY=sk-ant-...` ([console.anthropic.com](https://console.anthropic.com))
- `DASHBOARD_API_KEY=` (generiši: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)

**Preporučeno** (bez ovoga radi sa edge-tts fallback):
- `AZURE_SPEECH_KEY=`, `AZURE_SPEECH_REGION=westeurope`, `AZURE_STT_LANGUAGE=hr-HR`
- `GROQ_API_KEY=` (za STT, free tier)

Detalji o svim varijablama: [`features/voice-mode.md`](./features/voice-mode.md), [`features/logging-dashboard.md`](./features/logging-dashboard.md).

## 4. Vektorska baza i kategorije (jednokratno, ~5 min)

```bash
python scripts/embed_products.py    # ~5 min, generiše products.index.npz + meta.json
python scripts/build_categories.py  # ~10s, generiše categories.json
python scripts/init_db.py           # idempotentno, kreira var/bitlab.db
```

Šta ovo radi: [`features/ai-classification.md`](./features/ai-classification.md).

## 5. Pokreni backend

```bash
uvicorn app.main:app --reload
```

Provjera:
```bash
curl http://localhost:8000/healthz
```

Otvori chat widget: http://localhost:8000

## 6. Pokreni dashboard (drugi terminal)

```bash
cd dashboard
pnpm install
pnpm dev
```

Otvori http://localhost:5173/admin/

Idi na **Settings**, paste-uj `DASHBOARD_API_KEY` iz `.env`, save → svi tabovi rade.

Šta dashboard radi: [`features/logging-dashboard.md`](./features/logging-dashboard.md).

## Sledeći koraci

- Pošalji prvu poruku: "imate li gaming mis"
- Otvori voice mode (mikrofon dugme u widget-u)
- Otvori `/admin/live` i vidi tool calls timeline
- Ako pukne — [`operations/troubleshooting.md`](./operations/troubleshooting.md)
- Deploy na server — [`../DEPLOY.md`](../DEPLOY.md)
