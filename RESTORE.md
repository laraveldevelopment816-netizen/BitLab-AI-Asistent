# RESTORE — povratak na originalnu funkcionalnu aplikaciju

> Pretpostavka: pretpostavio sam da je `REATORE.md` typo za `RESTORE.md` — preimenuj ako želiš drugačije.

100% funkcionalna aplikacija je u `bck/`. Verifikacija je obavljena u trenutku reseta na granu `claude/tdd-zero-base`.

## Šta je u `bck/`

- **244 tracked fajla** koja git registruje kao obrisana — svi su prisutni u `bck/` (0 falilo u verifikaciji).
- **Untracked podaci** (van git-a, ali kritični za rad sistema):
  - `bck/data/products.index.npz` (7.3 MB) + `products.meta.json` (6.3 MB) — RAG indeks
  - `bck/data/all-products.json`, `brend.json`, `categories_new.json`, `category_terms.json`, `faq.md` — katalog
  - `bck/var/bitlab.db` — dashboard storage
  - `bck/dashboard/node_modules/` — Vite/React deps

## Šta je u rootu netaknuto

Zajedničko za oba stanja (originalno i TDD zero base): `app/__init__.py` (identičan HEAD-u), `public/`, `pyproject.toml`, `.env`, `.env.example`, `.gitattributes`, `scan.sh`, `CLAUDE.md`, `README.md`.

## Restore recipe (kad/ako zatreba originalna funkcionalnost)

```bash
cp -rT bck/app/    app/         # vraća originalni main.py/config.py/agent.py + sve module
cp -r  bck/{dashboard,n8n,deploy,data,scripts,tests,var,evals,bitlab_ai_asistent.egg-info} .
mv bck/docs/root-notes/* .      # loose root MD-ovi nazad u root
rmdir bck/docs/root-notes
cp -r  bck/docs .               # root docs/ sa brainstormima nazad
```

Tek tad pokreni `uvicorn app.main:app --port 7778` — sve radi kao prije reseta.

## Alternativa: git checkout

Sve tracked fajlove vraća automatski iz HEAD-a (gubi se PLAN.md, RESTORE.md, novi minimalni `app/` u rootu):

```bash
git checkout HEAD -- .
```

Untracked podaci (data/, var/, dashboard/node_modules) ostaju u `bck/` i moraju se kopirati ručno (gornji `cp` blok).
