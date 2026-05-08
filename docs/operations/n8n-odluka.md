# n8n setup — odluka i plan nastavka

**Datum:** 2026-05-08 (Friday)
**Cilj:** dignuti n8n na server-u (staging + prod) za email auto-reply workflow + sales workflow počev od 2026-W20 (11.05.2026.)

Pratiti zajedno sa [`n8n-setup.md`](./n8n-setup.md) (operativna uputstva) i [`../../README.md`](../../README.md#n8n-automatizacija) (overview).

---

## Trenutno stanje (2026-05-08)

### Server (`ai.bitlab.rs`) — gotovo

| Komponenta | Stanje |
|---|---|
| n8n binary | ✅ v2.19.2 instaliran (`/usr/bin/n8n`, npm global) |
| systemd `n8n-staging.service` | ✅ active, sluša `*:8031`, data `/home/ai/n8n-staging-data` |
| systemd `n8n-prod.service` | ✅ active, sluša `*:8030`, data `/home/ai/n8n-prod-data` |
| nginx `n8n-staging.conf` | ✅ `/etc/nginx/hosts/n8n-staging.conf` — HTTP-only, WS headers, dugi timeout |
| nginx `n8n-prod.conf` | ✅ `/etc/nginx/hosts/n8n-prod.conf` — HTTP-only, WS headers, dugi timeout |
| Firewall | ⚠️ default DROP, samo 80/443 ACCEPT — direktan pristup portovima 8030/8031 nemoguć izvana |

Verifikacija nginx-a (proxy radi, čeka samo DNS):

```bash
ssh ai@staging.aiasistent.bitlab.rs 'curl -sI -H "Host: n8n-staging.bitlab.rs" http://127.0.0.1/' | head -5
# → HTTP/1.1 200 OK (vraća n8n setup page)
```

### Repo — gotovo

- `n8n/email-autoreply.json` — URL parametrizovan kroz `={{ $env.AI_ASSISTANT_URL }}/api/email` (isti JSON na oba environmenta)
- `deploy/n8n-staging.service` — env vars `AI_ASSISTANT_URL=http://127.0.0.1:8001`, `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`
- `deploy/n8n-prod.service` — env vars `AI_ASSISTANT_URL=http://127.0.0.1:8000`, `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`
- `README.md` — dodata n8n sekcija (URL-ovi, sales workflow plan)
- `docs/STAGING-ACCESS.md` + `docs/PROD-ACCESS.md` — n8n linkovi
- `docs/operations/n8n-setup.md` — popunjena nginx + DNS + SSL sekcija (bila TODO)
- `docs/README.md` — link na n8n-setup

> **Napomena:** ažurirani systemd unit-i u repo-u **nisu još kopirani na server**. Server pokreće stare unit-e bez `AI_ASSISTANT_URL` env vara. Sync će se uraditi u koraku 4 finalnog plana ispod (kad budemo importovali workflow).

### DNS — blokirano

| Record | Stanje 2026-05-08 06:30 UTC |
|---|---|
| `n8n-staging.bitlab.rs A 136.243.203.28` | ❌ NXDOMAIN sa svih NS (`ns1/2/3.bitlab.host`) |
| `n8n.bitlab.rs A 136.243.203.28` | ❌ NXDOMAIN sa svih NS |

Dijagnostika: zone fajl za `bitlab.rs` na `ns1.bitlab.host` ne sadrži ove zapise (autoritativno NXDOMAIN, ne propagacija). Postojeći zapisi (`www.bitlab.rs`, `staging.aiasistent.bitlab.rs`, …) rade — zona je inače funkcionalna. Admin **Rale** će dodati kad bude vremena, ne hitamo.

---

## Plan kad DNS bude resolvao (final state)

```bash
# 1. Verify direct na NS
ssh ai@staging.aiasistent.bitlab.rs 'host n8n-staging.bitlab.rs ns1.bitlab.host'
ssh ai@staging.aiasistent.bitlab.rs 'host n8n.bitlab.rs ns1.bitlab.host'
# → mora vraćati 136.243.203.28

# 2. Certbot SSL za oba domena odjednom
ssh ai@staging.aiasistent.bitlab.rs '
sudo certbot --nginx -d n8n-staging.bitlab.rs -d n8n.bitlab.rs \
  --redirect --email admin@bitlab.rs --non-interactive --agree-tos
'

# 3. Verify HTTPS
curl -I https://n8n-staging.bitlab.rs/  # → 200
curl -I https://n8n.bitlab.rs/           # → 200

# 4. Sync ažurirane systemd unit-e (sa AI_ASSISTANT_URL)
scp deploy/n8n-staging.service ai@staging.aiasistent.bitlab.rs:/tmp/
scp deploy/n8n-prod.service ai@staging.aiasistent.bitlab.rs:/tmp/
ssh ai@staging.aiasistent.bitlab.rs '
sudo cp /tmp/n8n-staging.service /etc/systemd/system/
sudo cp /tmp/n8n-prod.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart n8n-staging n8n-prod
sudo systemctl is-active n8n-staging n8n-prod
'

# 5. UI: kreiraj admin account u browser-u
# → https://n8n-staging.bitlab.rs (i kasnije n8n.bitlab.rs)

# 6. Workflow import + Gmail OAuth
# → vidi docs/operations/n8n-setup.md sekcija "Workflow import"
# → Google Cloud Console: redirect URI
#   https://n8n-staging.bitlab.rs/rest/oauth2-credential/callback
#   https://n8n.bitlab.rs/rest/oauth2-credential/callback

# 7. Smoke test
# → pošalji email sa "upit" u subject-u → očekuj AI reply za ~60s
# → log: ssh ... 'sudo journalctl -u n8n-staging -f'
```

---

## Workaround (bez DNS-a) — subpath ✅ AKTIVAN od 2026-05-08

**Trenutno radni URL-ovi:**

| | URL |
|---|---|
| Staging n8n | https://staging.aiasistent.bitlab.rs/n8n/ |
| Production n8n | https://aiasistent.bitlab.rs/n8n/ |

**OAuth callback URL-ovi** (za Google Cloud Console kad budemo postavljali Gmail OAuth2 credentials):
- Staging: `https://staging.aiasistent.bitlab.rs/n8n/rest/oauth2-credential/callback`
- Production: `https://aiasistent.bitlab.rs/n8n/rest/oauth2-credential/callback`

**Šta je urađeno na server-u (2026-05-08):**

1. Backup-ovani postojeći nginx configi: `/etc/nginx/backups/aiasistent-{staging,prod}.conf.bak.20260508`
2. Dodat `location /n8n/` blok u `aiasistent-staging.conf` (proxy na 8031) i `aiasistent-prod.conf` (proxy na 8030)
3. Systemd drop-in override za oba n8n servisa: `/etc/systemd/system/n8n-{staging,prod}.service.d/subpath-override.conf` sa:
   - `N8N_HOST=staging.aiasistent.bitlab.rs` / `aiasistent.bitlab.rs`
   - `N8N_PATH=/n8n/`
   - `WEBHOOK_URL=https://...../n8n/`
   - `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`
   - `AI_ASSISTANT_URL=http://127.0.0.1:8001` (staging) / `8000` (prod)
4. nginx reload + n8n daemon-reload + restart oba servisa
5. Verify: `curl -I https://staging.aiasistent.bitlab.rs/n8n/` → 200, asset-i pravilno prefiksovani sa `/n8n/`

---

**Migracija subpath → subdomena (kad Rale objavi DNS):**

1. Verify DNS: `host n8n-staging.bitlab.rs ns1.bitlab.host` → 136.243.203.28
2. Certbot SSL: `sudo certbot --nginx -d n8n-staging.bitlab.rs -d n8n.bitlab.rs --redirect ...`
3. Obriši systemd drop-in: `sudo rm /etc/systemd/system/n8n-{staging,prod}.service.d/subpath-override.conf`
4. Sync ažurirane systemd unit-e iz repa (sa subdomain `N8N_HOST` + `AI_ASSISTANT_URL`):
   ```bash
   scp deploy/n8n-staging.service ai@staging.aiasistent.bitlab.rs:/tmp/
   scp deploy/n8n-prod.service ai@staging.aiasistent.bitlab.rs:/tmp/
   ssh ... 'sudo cp /tmp/n8n-*.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart n8n-staging n8n-prod'
   ```
5. Obriši `location /n8n/` iz `aiasistent-{staging,prod}.conf` (vrati na backup ili rucno) — opciono ako želimo da subpath nestane; može se ostaviti i kao redundant pristup
6. U Google Cloud Console: dodaj nove redirect URI `https://n8n-staging.bitlab.rs/rest/oauth2-credential/callback` (i prod) i obriši stare subpath URI-je nakon migracije

---

## Tehnički detalji subpath workaround-a (referenca)

Ako trebaš da reproduciraš na drugom serveru ili rebuild-aš:

1. **Nginx** — dodati u `aiasistent-staging.conf` i `aiasistent-prod.conf`:

```nginx
location /n8n/ {
    proxy_pass http://127.0.0.1:8031/;  # staging; prod = 8030; trailing slash kritičan
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400s;
    proxy_buffering off;
}
```

2. **n8n env** — update systemd unit-e (`Environment=...`):

```
N8N_HOST=staging.aiasistent.bitlab.rs   # ili aiasistent.bitlab.rs za prod
N8N_PATH=/n8n/
WEBHOOK_URL=https://staging.aiasistent.bitlab.rs/n8n/   # ili prod
N8N_PROTOCOL=https
```

3. **Restart**: `sudo systemctl daemon-reload && sudo systemctl restart n8n-staging n8n-prod && sudo systemctl reload nginx`

4. **OAuth callback URL** kod Google Cloud Console-a postaje:
   `https://staging.aiasistent.bitlab.rs/n8n/rest/oauth2-credential/callback`
   (i `aiasistent.bitlab.rs/n8n/...` za prod)

5. SSL ne treba — postojeći cert za `staging.aiasistent.bitlab.rs` i `aiasistent.bitlab.rs` već važi za subpath.

**Migracija subpath → subdomena (kad DNS bude live):** vrati `N8N_HOST`, `N8N_PATH`, `WEBHOOK_URL` na subdomain vrijednosti, restart, OAuth callback URL u Google Console mijenjaš ili dodaješ paralelno (ostavi oba dok ne migriraš sve).

---

## Lokalno za danas

Korisnik koristi vlastiti **lokalni n8n** (laptop) za testiranje workflow-a — već je verifikovano da radi.

Ako treba reset import-a iz repo-a u lokalni n8n:

```bash
# 1. Lokalni n8n (default port 5678)
docker run -d --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n \
  -e AI_ASSISTANT_URL=http://host.docker.internal:8000 \
  -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
  n8nio/n8n
# (ili n8n.io/download desktop app)

# 2. Lokalni FastAPI
uvicorn app.main:app --reload   # → 127.0.0.1:8000

# 3. n8n UI: http://localhost:5678 → Import → n8n/email-autoreply.json
# 4. Gmail OAuth credentials (zaseban Google Cloud project ili test users)
# 5. Aktiviraj workflow → pošalji test email
```

Razlika u env varu za lokal: `AI_ASSISTANT_URL=http://host.docker.internal:8000` (Docker n8n traži `host.docker.internal`) ili `http://localhost:8000` (Desktop n8n).

---

## Donijetne odluke

| # | Odluka | Razlog |
|---|---|---|
| 1 | n8n native (npm + systemd), ne Docker | Proxmox unprivileged LXC ne podržava overlay/fuse za Docker (vidi `n8n-setup.md` "Why not Docker") |
| 2 | Subdomene `n8n[-staging].bitlab.rs` su preferirana finalna ruta | Cleaner OAuth callbacks, standard pattern, kraći URL-ovi |
| 3 | Subpath `/n8n/` je rezervni workaround | Ako admin DNS dugo ne dođe — može se uraditi za 5 min, postojeći SSL pokriva |
| 4 | URL u workflow-u kroz `$env.AI_ASSISTANT_URL` | Isti JSON radi na staging+prod+lokal — jedan source of truth |
| 5 | Email auto-reply ide preko Gmail Trigger (ne IMAP) | Gmail OAuth2 standard, nije legacy IMAP polling; zahtijeva Google Cloud Console setup |
| 6 | Sales workflow počinje 2026-W20 (11.05.2026.) | Dogovor sa biznis stranom |
| 7 | Admin (Rale) zove se za finalne stvari, ne za sitnice | Workaround putevi su prvi izbor; admin za publish DNS-a kad bude vrijeme |
| 8 | Staging prvo, prod kasnije | Test workflow na staging-u → promote na prod kad biznis logika sjedne |

---

## Otvoreno

- **Gmail OAuth credentials** — Google Cloud Console projekat treba registrovati. OAuth client ID/secret za staging + prod posebno (ili jedan client sa oba redirect URI-ja). Ide kasnije, kad budemo aktivirali workflow.
- **Sales workflow content** — još neispecificirano (lead nurturing? abandoned cart? follow-up?). Dogovor sa biznis stranom prije 2026-W20.
- **Branch za commit** — n8n setup izmjene su trenutno na `feature/ai-search-brand-category-improvements` grani (uncommitted) zajedno sa nevezanim AI-search radom. Treba split u poseban branch (`feature/n8n-prod-deploy` ili sl.) prije PR-a.
