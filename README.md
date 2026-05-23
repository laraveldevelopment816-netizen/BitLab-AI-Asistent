# BitLab AI Asistent

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

Detalji: [`docs/getting-started.md`](./docs/getting-started.md)
