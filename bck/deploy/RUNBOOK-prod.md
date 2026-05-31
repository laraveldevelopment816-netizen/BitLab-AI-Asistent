# RUNBOOK — aiasistent prod

**Cilj:** dignuti `aiasistent.bitlab.rs` (BitLab AI Asistent prod) za ~10 min.

## ⚠️ Korak 0 — KRITIČNO prije bilo čega

**Provjeri da je staging mergovan u main:**

```
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent
git fetch origin
git log origin/main..origin/staging --oneline
```

**Ako lista nije prazna → STOP.** Mergaj prvo:

```
git checkout main && git merge staging && git push origin main
```

Bez ovog, prod kloniraće zastarelu main verziju (incident 2026-05-06: dashboard nije bio na main → `build_dashboard` skipovan u prod-u).

## Pre-flight (na serveru)

- [ ] DNS: `dig +short aiasistent.bitlab.rs A` → IP servera
- [ ] aiasistent-staging radi (`/home/ai/aiasistent-staging/shared/.env` postoji — ENV_TEMPLATE)
- [ ] Port 8000 slobodan: `sudo ss -tlnp | grep :8000`
- [ ] `~/deploy.sh` na serveru ima `setup-domain` komandu: `grep -n "setup-domain)" ~/deploy.sh`

## Komande

**1. Iz lokalnog repoa, scp env helper:**

```
cd /mnt/c/Users/Kule/Projects/bitlab-ai-asistent
scp deploy/prod.env.example ai@aiasistent.bitlab.rs:~/aiasistent-prod.env
```

**2. SSH + setup:**

```
ssh ai@aiasistent.bitlab.rs
```

```
source ~/aiasistent-prod.env
bash ~/deploy.sh setup-domain
```

Skripta će **pauzirati** nakon kopiranja `.env` template-a iz staging-a — pregledaj prod vrijednosti (API keys, `ENVIRONMENT=production`, drugačiji `DASHBOARD_API_KEY` ako koristiš), pa `[y]` za nastavak.

## Verifikacija

```
curl https://aiasistent.bitlab.rs/healthz                # 200 OK
sudo systemctl status aiasistent-prod                     # active (running)
sudo journalctl -u aiasistent-prod -n 20 --no-pager      # bez error/traceback
```

Otvoreni dashboard u browser-u: `https://aiasistent.bitlab.rs/admin/`

## Rollback (ako pukne)

```
sudo systemctl stop aiasistent-prod
sudo rm /etc/systemd/system/aiasistent-prod.service
sudo rm /etc/nginx/hosts/aiasistent-prod.conf
sudo certbot delete --cert-name aiasistent.bitlab.rs
sudo rm -rf /home/ai/aiasistent-prod
sudo systemctl daemon-reload && sudo systemctl reload nginx
```

## Sledeći release-ovi (nakon prvog setup-a)

```
ssh ai@aiasistent.bitlab.rs
source ~/aiasistent-prod.env
bash ~/deploy.sh release
```

`release` flow ne dira systemd/nginx/cert — samo clone novog koda, switch symlink-a, restart servisa.

## Manual setup (debug)

Ako `setup-domain` pukne usred posla, koristi `MANUAL-setup-domain.md` — razbija flow u 14 koraka koje pozivaš ručno.
