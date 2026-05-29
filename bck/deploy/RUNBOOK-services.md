# RUNBOOK — server services

Click-to-copy referenca za upravljanje systemd servisima na `ai@aiasistent.bitlab.rs`. Svaki blok ispod je jedna komanda — kopiraj i pokreni na serveru.

**Server:** `ai@aiasistent.bitlab.rs` (jedan VPS, ~1–2 GB RAM, sve dijeli isti host)

## Servisi koje vrtimo

| Servis                       | Port  | Domain                          | RAM (~) | Svrha                                |
|------------------------------|-------|---------------------------------|---------|--------------------------------------|
| `aiasistent-prod.service`    | 8000  | `aiasistent.bitlab.rs`          | 600 MB  | FastAPI chat + voice + dashboard     |
| `aiasistent-staging.service` | 8001  | `staging.aiasistent.bitlab.rs`  | 600 MB  | FastAPI staging                      |
| `n8n-prod.service`           | 8030  | `n8n.bitlab.rs`                 | 800 MB  | n8n workflows prod                   |
| `n8n-staging.service`        | 8031  | `n8n-staging.bitlab.rs`         | 800 MB  | n8n workflows staging                |

`bitlab-ai.service` u ovom folderu je legacy template — current setup koristi per-environment jedinice (`aiasistent-prod`, `aiasistent-staging`) koje se generišu kroz `~/deploy.sh setup-domain`.

**Memorija — bitno:** VPS ne stane sva četiri servisa odjednom + nginx + sistem. Tipično se staging gase kad treba memorija; aktivan incident pattern je da se zaboravi vratiti pa kasnije nginx daje 502 na staging domenu.

## Status — šta radi, šta ne radi

Sve inactive + failed jedinice na serveru (osnova za "šta sam zaboravio vratiti"):

```bash
sudo systemctl list-units --type=service --state=inactive,failed --no-pager
```

Detalji jednog servisa (status + zadnjih ~10 logova):

```bash
sudo systemctl status aiasistent-staging --no-pager
```

Ko sluša na našim portovima:

```bash
sudo ss -tlnp | grep -E ':8000|:8001|:8030|:8031'
```

RAM trenutno po našim servisima:

```bash
systemctl status aiasistent-prod aiasistent-staging n8n-prod n8n-staging --no-pager | grep -E '\.service|Memory:'
```

## Start / stop / restart

Pojedinačno:

```bash
sudo systemctl start aiasistent-staging
```

```bash
sudo systemctl stop aiasistent-staging
```

```bash
sudo systemctl restart aiasistent-staging
```

Bulk operacije:

```bash
sudo systemctl start aiasistent-prod aiasistent-staging n8n-prod n8n-staging
```

Zaustavi sve staging servise (oslobađa ~1.4 GB):

```bash
sudo systemctl stop aiasistent-staging n8n-staging
```

## Logs

Posljednjih 50 linija:

```bash
sudo journalctl -u aiasistent-staging -n 50 --no-pager
```

Live tail (Ctrl+C za prekid):

```bash
sudo journalctl -u aiasistent-staging -f
```

Samo error / exception / traceback:

```bash
sudo journalctl -u aiasistent-staging -n 500 --no-pager | grep -iE 'error|exception|traceback|failed'
```

## Health checks — iz lokalnog WSL-a, bez SSH-a

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://aiasistent.bitlab.rs/healthz
curl -sS -o /dev/null -w "%{http_code}\n" https://staging.aiasistent.bitlab.rs/healthz
curl -sS -o /dev/null -w "%{http_code}\n" https://n8n.bitlab.rs/
curl -sS -o /dev/null -w "%{http_code}\n" https://n8n-staging.bitlab.rs/
```

Ako curl daje `502` → nginx je živ, ali upstream servis (Python / n8n) je mrtav. Ako daje connection error → ili je nginx down, ili DNS, ili sam host.

## Memorija na serveru

```bash
free -m
```

Top 10 procesa po RSS memoriji:

```bash
ps aux --sort=-rss | head -11
```

## Nginx

Test konfiguracije + reload (bezbjedno; ne kill-uje konekcije):

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Restart (kill konekcija — koristi samo ako reload ne pomaže):

```bash
sudo systemctl restart nginx
```

## Incident pattern: "staging pao zbog memorije"

Najčešći scenario: VPS dođe blizu OOM, ručno se stopiraju memory-heavy servisi (n8n + aiasistent staging), pa se zaboravi vratiti. Simptom kasnije: `502 Bad Gateway` na staging domenu.

Recovery sekvenca:

1. Provjeri memoriju (lokalno, kroz SSH komandu):

```bash
ssh ai@aiasistent.bitlab.rs 'free -m'
```

2. Ako ima slobodne (>500 MB):

```bash
sudo systemctl start aiasistent-staging n8n-staging
```

3. Verifikuj iz lokalnog WSL-a:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" https://staging.aiasistent.bitlab.rs/healthz
```

Očekuje se `200`. Ako i dalje `502` → `journalctl -u aiasistent-staging -n 100` da vidiš zašto servis ne starta (najčešće: `.env` issue, port zauzet, ili python venv corrupted).

## TODO — nedostaje

- Chrome login servis (vjerovatno `playwright-router` iz sibling repoa) — još nema `.service` fajla u ovom folderu, ne znam puno service ime. Dodati čim se identifikuje.
- SSL cert renewal procedure (certbot autotask, ali komanda za ručnu provjeru `sudo certbot certificates`).
- Kako resetovati n8n encryption key ako se izgubi (rijetko, ali bitno).
