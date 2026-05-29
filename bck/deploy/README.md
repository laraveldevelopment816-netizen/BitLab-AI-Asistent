# Deploy — BitLab AI Asistent

Sve za deploy aiasistent-a na ai.bitlab.rs server.

## Šta gdje

| Fajl | Šta je |
|---|---|
| `RUNBOOK-prod.md` | **Glavni dokument** — copy-paste flow za prod deploy (`aiasistent.bitlab.rs`) |
| `MANUAL-setup-domain.md` | Razbijanje `setup-domain` u 14 koraka — za debug ili kad nešto pukne usred flow-a |
| `prod.env.example` | Env helper za prod (`PROJECT_NAME=aiasistent-prod`, port 8000, branch main) |
| `staging.env.example` | Env helper za staging (port 8001, branch staging) |
| `bitlab-ai.service` | Systemd unit template |
| `nginx-site.conf` | Nginx config template |
| `n8n-prod.service`, `n8n-staging.service` | Systemd unit-i za n8n (email auto-reply) |

## Skripta

`scripts/deploy.sh` (u root-u repoa) — orchestrator. Tri komande:

- `bash deploy.sh setup-domain` — prvi put na novom domenu (env, folder, clone, systemd, nginx, certbot, health)
- `bash deploy.sh release` — svaki sledeći deploy (clone, switch, restart, health)
- `bash deploy.sh rollback` — vrati na prethodni release

## Brzi start za prod

Vidi `RUNBOOK-prod.md`. TL;DR:

```
scp deploy/prod.env.example ai@aiasistent.bitlab.rs:~/aiasistent-prod.env
ssh ai@aiasistent.bitlab.rs
source ~/aiasistent-prod.env
bash ~/deploy.sh setup-domain   # prvi put
```

## Domeni

| Env | Domen | Port | Branch |
|---|---|---|---|
| Staging | `staging.aiasistent.bitlab.rs` | 8001 | `staging` |
| Prod | `aiasistent.bitlab.rs` | 8000 | `main` |

## Git workflow obavezan

Prije svakog prod deploy-a (vidi root README.md "Git workflow" sekciju):

```
git fetch origin
git log origin/main..origin/staging --oneline   # MORA biti prazno
```
