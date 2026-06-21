# Baseline & Restore — `bck/` → produkcija

**Svrha (čitaj prvo):** Aplikacija je **ZAVRŠENA** — sva poslovna logika živi u `bck/` (244 tracked fajla
+ untracked podaci). **Nema novih fičara; cilj je izvući postojeće iz `bck/` i osposobiti za produkciju**,
sistematski da ništa ne promakne. Ovaj dokument je referenca: (1) kako je urađen zero-base reset i šta je
gdje, (2) kako vratiti/izvući staru funkcionalnost.

> Spoj bivših `PLAN.md` (2026-05-23) + `RESTORE.md`. Detaljna pravila petlje: [`../../ralph/AGENTS.md`](../../ralph/AGENTS.md).

---

## Dio 1 — Zero-base reset (bivši PLAN.md)

**Cilj:** krenuti od nule — prazan system prompt, nikakvi tools, nikakva poslovna logika; eval-driven
(failing eval → minimum dodaj → PASS → sljedeći). Grana `claude/tdd-zero-base`.

Šta je gdje poslije reseta:
- **Poslovna logika → `bck/app/`**: `agent.py`, `system_prompts.py`, `tools.py`, `categories.py`, `brands.py`, `rag.py`, `faq.py`, `contacts.py`, `email_poller.py`, `server/`, `storage/`.
- **U `app/` ostaje minimum za boot**: `main.py` (FastAPI, `/healthz`, `/api/chat`, static), `config.py`, tanki `agent.py` (`run_agent`, prazan system, bez tools).
- `public/widget.html` + `widget.js` ostaju (frontend).
- `dashboard/`, `n8n/`, `deploy/`, `var/` → `bck/`. Root markdown (EVAL-*, TEST-*, SSOT-*, README-STANDARD) → `bck/docs/`.
- `bck/` u `.gitignore` (vraća se kroz `git log`); committuje se samo aktivna struktura.

Pravila: ni red prompta/tool/dispatch koji failing eval nije tražio; jedan fix u trenutku; eval set je invariant.

---

## Dio 2 — Restore / izvlačenje (bivši RESTORE.md)

100% funkcionalna app je u `bck/` (verifikovano u trenutku reseta). Untracked, ali kritično za rad:
`bck/data/products.index.npz` + `products.meta.json` (RAG indeks), `all-products.json`/`brend.json`/
`categories_new.json`/`category_terms.json`/`faq.md` (katalog), `bck/var/bitlab.db` (dashboard), `bck/dashboard/node_modules/`.

Restore recept (kad/ako zatreba originalna funkcionalnost):

```bash
cp -rT bck/app/    app/         # originalni main.py/config.py/agent.py + svi moduli
cp -r  bck/{dashboard,n8n,deploy,data,scripts,tests,var,evals,bitlab_ai_asistent.egg-info} .
mv bck/docs/root-notes/* .      # loose root MD-ovi nazad
rmdir bck/docs/root-notes
cp -r  bck/docs .               # root docs/ sa brainstormima
# pa: uvicorn app.main:app --port 7778
```

Alternativa (tracked fajlovi iz HEAD-a; untracked podaci ostaju u `bck/`, kopiraju se ručno):

```bash
git checkout HEAD -- .
```
