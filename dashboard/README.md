# BitLab AI Asistent — Admin Dashboard

React + TypeScript + Vite SPA za telemetriju (`/api/dashboard/*`).
Servira se na ruti `/admin/` (vidi `vite.config.ts:base`).

## Najbrži dev flow (5 minuta)

### 1. Pokreni BAA backend

```bash
# Iz root-a repo-a:
source .venv/bin/activate
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --log-level info
```

> **WSL2 caveat:** ako port 8000 zauzme Docker Desktop proxy (česta pojava
> 8000-8090 na WSL2), uvicorn neće moći da slušaju → pokreni na slobodnom
> portu (npr. `--port 7778`) i privremeno izmijeni `vite.config.ts`:
>
> ```ts
> server: { proxy: { '/api': 'http://localhost:7778' } }
> ```
>
> Vrati nazad na 8000 prije commit-a.

### 2. Pokreni Vite dev server (novi terminal)

```bash
cd dashboard
pnpm install        # samo prvi put (node_modules je u repu, brzo)
pnpm dev            # Vite na port 5173 sa HMR
```

Otvori `http://localhost:5173/admin/` u browser-u.

### 3. Postavi bearer key (jednom po browser-u)

SPA traži `DASHBOARD_API_KEY` iz `.env` u Authorization header-u. U dev
mode-u nema auto-inject-a, pa preko DevTools Console:

```javascript
localStorage.setItem('bitlab.dashboardKey', DASHBOARD_API_KEY)
location.reload()
```

Vrijednost je iz root `.env` (`DASHBOARD_API_KEY=...`). Settings stranica
u UI-ju takođe radi za manualni override.

Bez ključa: sve `/api/dashboard/*` vraćaju 401, SPA pokazuje "Backend
nije dostupan".

## Druge opcije

| Opcija | Komanda | Kad treba |
|---|---|---|
| Vite dev (HMR) | `pnpm dev` | rutinski rad na SPA-i |
| Production build preview | `pnpm build && pnpm preview` | test build artifact-a prije push-a |
| Pun Docker (nginx) | `docker build -t baa-admin . && docker run -p 8080:80 baa-admin` | provjera nginx fallback-a / static cache header-a. Bez Caddy-ja `/api/*` neće prolaziti — koristi samo za UI smoke. |

## Tipični problemi

**404 na `/api/dashboard/overview`** — Vite proxy ide na pogrešan port.
Provjeri `vite.config.ts:server.proxy` da matchuje port na kojem zaista
radi uvicorn (`ss -tln | grep LISTEN`).

**401 Unauthorized** — bearer key nije postavljen ili istekao. Vidi
korak 3.

**Stale cache nakon promjene** — Vite HMR obično pokriva sve, ali za
React Router rute može trebati hard reload (Ctrl+Shift+R).

## Arhitektura

- Build: `pnpm build` → `dist/` (Vite + TypeScript compile)
- Deploy: `Dockerfile` multi-stage (node:20-alpine build → nginx:1.27-alpine serve)
- Bearer key inject: `__BITLAB_KEY` placeholder u `dist/index.html` se mijenja
  u deploy.sh sa pravom vrijednošću iz shared `.env` (vidi `src/api.ts:9`)
- SPA fallback: nginx `try_files $uri /index.html` (sve nepoznate rute idu na
  React Router client-side; vidi `nginx.conf`)

## Linting

```bash
pnpm lint
```

ESLint config je u `eslint.config.js` (default Vite + React preset).
