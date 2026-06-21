# Troubleshooting

## Tipični problemi i rješenja

| Simptom | Rješenje |
|---|---|
| Server ne starta — `products.index.npz` ne postoji | `python scripts/embed_products.py` (~5 min) |
| `anthropic.AuthenticationError: invalid x-api-key` | `.env` format mora biti `KEY=value` (sa `=`, bez navodnika) |
| `anthropic.BadRequestError: credit balance is too low` | [console.anthropic.com](https://console.anthropic.com) → Plans & Billing |
| TTS ne radi — `503` | Postavi `AZURE_SPEECH_KEY` u `.env`, ili pusti edge-tts fallback (radi bez ključa) |
| Voice mod — mikrofon ne radi | Web Speech API podržava samo Chrome i Edge. Firefox nije podržan. Treba HTTPS ili `localhost`. |
| `ModuleNotFoundError` | Aktiviraj venv: `source .venv/bin/activate` (Linux) ili `.\.venv\Scripts\Activate.ps1` (Win) |
| Port 8000 zauzet | `fuser -k 8000/tcp` (Linux) ili `netstat -ano \| findstr :8000` (Win) |
| `/admin/*` vraća 401 | Unesi `DASHBOARD_API_KEY` u Settings tab → save → reload |
| Dashboard build pada | Provjeri Node 22 (`node -v`) + pnpm; obriši `node_modules/` + `pnpm-lock.yaml` i `pnpm install` |
| Prvi `/api/chat` poslije restart vraća error / "Pretraga prazan rezultat" | sentence-transformers preload na cold start traje 30-50s. Sledeći upit ide normalno. |
| `<voice>` tagovi vidljivi u chat-u | Hard refresh widget-a (Ctrl+Shift+R) za widget cache + restart `uvicorn` |
| TTS čita "1.936 KM" kao "jedna marka" | Sesija 8 fix u `app/main.py:_normalize_for_tts`. Ako je server na starom kodu, treba re-deploy |
| Razbijen layout sa `---` separatorom | Sesija 8 fix. Hard refresh + restart server |
| Dashboard `/admin/` daje 404 | Provjeri symlink: `readlink -f /home/ai/aiasistent-prod/current/dashboard/dist/index.html`. Ako fali, `cd dashboard && pnpm build` |
| Compare endpoint timeout | Sonnet poziv može trajati 15-20s. nginx `proxy_read_timeout 120s` mora biti u config-u |
| Slika ne postoji za neke proizvode | Webshop migracija (cover legacy). Vidi [`data-quality.md`](./data-quality.md) |
| n8n ne hvata nove emailove | Provjeri Gmail App Password (ne računarska lozinka). Polling interval = 60s |

## Logovi

### Lokalno (uvicorn)

```bash
# Foreground
uvicorn app.main:app --reload   # sve ide u stdout

# Tool call greške se loguju u stdout sa "[TOOL ERROR]" prefiksom
grep "TOOL ERROR\|TRACE\|AGENT" /tmp/uvicorn.log
```

### Produkcija (systemd)

```bash
# Tail live
sudo journalctl -u aiasistent-prod -f

# Zadnjih 100
sudo journalctl -u aiasistent-prod -n 100 --no-pager

# Po vremenskom prozoru
sudo journalctl -u aiasistent-prod --since "1 hour ago"

# Filter po error level
sudo journalctl -u aiasistent-prod -p err --no-pager
```

### Nginx

```bash
tail -f /home/ai/aiasistent-prod/shared/logs/nginx-access.log
tail -f /home/ai/aiasistent-prod/shared/logs/nginx-error.log
```

### Dashboard (browser DevTools)

Otvori `/admin/`, F12 → Console + Network tab. Provjeri:
- Da li `/api/dashboard/*` requests imaju `Authorization: Bearer ...` header
- Status: 401 → API key fail, 500 → backend exception

## Debug shortcuts

```bash
# Health
curl -fsS https://aiasistent.bitlab.rs/healthz | jq

# Test chat sa kategorija filter
curl -sX POST https://aiasistent.bitlab.rs/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"imate li gaming mis","channel":"chat"}' | jq -r .reply

# Test dashboard auth
KEY=$(grep ^DASHBOARD_API_KEY /home/ai/aiasistent-prod/shared/.env | cut -d= -f2)
curl -sf https://aiasistent.bitlab.rs/api/dashboard/stats \
  -H "Authorization: Bearer $KEY" | jq

# Provjeri symlink
readlink -f /home/ai/aiasistent-prod/current

# Provjeri systemd
sudo systemctl status aiasistent-prod --no-pager
```

## Restart sve

```bash
sudo systemctl restart aiasistent-prod
sudo systemctl reload nginx
```

Reload nginx ne ruši konekcije (gracefull). Restart aiasistent-prod ima ~5s downtime + 30-50s prvi `/api/chat` (model preload).

## Kad sve drugo ne radi

```bash
# Rollback na prethodni release
ls /home/ai/aiasistent-prod/releases/
ln -sfn /home/ai/aiasistent-prod/releases/<PRETHODNI_TIMESTAMP> /home/ai/aiasistent-prod/current
sudo systemctl restart aiasistent-prod
```
