# n8n setup — staging i prod

n8n hostuje IMAP→email-autoreply workflow (vidi [`n8n/email-autoreply.json`](../../n8n/email-autoreply.json)). Pošto Proxmox unprivileged LXC blokira Docker (cgroupv2 + overlay/fuse problemi), n8n se instalira **native preko npm + systemd**.

| | staging | prod |
|---|---|---|
| Domena | `n8n-staging.bitlab.rs` | `n8n.bitlab.rs` |
| Port (lokalno) | 8031 | 8030 |
| User folder | `/home/ai/n8n-staging-data` | `/home/ai/n8n-prod-data` |
| Systemd unit | `deploy/n8n-staging.service` | `deploy/n8n-prod.service` |

Unit fajlovi su u `deploy/` u repo-u — kopiraju se na server bez whitespace prefiksa (chat-paste često dodaje vodeće razmake u `<<EOF` heredoc).

## Prvi setup (jednom po projektu)

Naslanja se na to da je projekat već clone-an u `/home/ai/aiasistent-staging/current/` (ili `aiasistent-prod/current/`) jer iz tog releasea kopiramo unit fajl.

```bash
# 1. Instaliraj n8n globally (Node 22 + npm su već na serveru)
sudo npm install -g n8n

# 2. Data folder
mkdir -p /home/ai/n8n-staging-data    # ili n8n-prod-data za prod

# 3. Kopiraj unit fajl iz repo-a
sudo cp /home/ai/aiasistent-staging/current/deploy/n8n-staging.service /etc/systemd/system/

# 4. Enable + start
sudo systemctl daemon-reload
sudo systemctl enable --now n8n-staging
sudo systemctl is-active n8n-staging       # treba: active

# 5. Provjeri da sluša na portu
sudo ss -tlnp | grep :8031
```

Za prod isto, samo zameni `staging` → `prod` u nazivima i koristi `aiasistent-prod`.

## Update n8n verzije

```bash
sudo npm install -g n8n@latest
sudo systemctl restart n8n-staging n8n-prod
```

## Workflow import (jednom po projektu)

1. Otvori `https://n8n-staging.bitlab.rs` (nakon nginx + DNS + certbot setupa, vidi sekciju ispod)
2. Kreiraj admin account (n8n built-in user management)
3. Idi na **Workflows → Import from File**
4. Upload `n8n/email-autoreply.json` iz repo-a
5. Otvori workflow, podesi credentials:
   - **Gmail Trigger** + **Gmail Send** nodovi: kreiraj Gmail OAuth2 credentials (Google Cloud Console → OAuth client ID, redirect URI `https://n8n-staging.bitlab.rs/rest/oauth2-credential/callback` ili `https://n8n.bitlab.rs/...` za prod)
   - **HTTP Request** node: URL je već `={{ $env.AI_ASSISTANT_URL }}/api/email` — ne diraj
6. Activate workflow (toggle gore desno)

## Nginx + DNS + SSL

DNS A records (oba pokazuju na server IP, isto kao `*.aiasistent.bitlab.rs`):

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `n8n-staging` | `136.243.203.28` | Auto |
| A | `n8n` | `136.243.203.28` | Auto |

Nginx config-i (oba kreirana 2026-05-08, vidi `/etc/nginx/hosts/n8n-staging.conf` i `n8n-prod.conf`): listen 80 → proxy `127.0.0.1:8031` (staging) / `8030` (prod), sa WebSocket headers (`Upgrade`, `Connection upgrade`), `proxy_read_timeout 86400s`, `proxy_buffering off`, `client_max_body_size 50M`.

SSL (certbot, dodaje 443 + 80→443 redirect automatski):

```bash
sudo certbot --nginx -d n8n-staging.bitlab.rs -d n8n.bitlab.rs --redirect --email admin@bitlab.rs --non-interactive --agree-tos
```

(Pokreće se kad DNS propagira — certbot HTTP-01 challenge zavisi od public DNS resolve-a.)

## URL configuration u workflow-ima

`n8n/email-autoreply.json` koristi `={{ $env.AI_ASSISTANT_URL }}/api/email` umjesto hardcode-ovanog URL-a, pa se isti JSON importuje na oba environmenta. Env var ide u systemd unit:

- `deploy/n8n-staging.service`: `Environment=AI_ASSISTANT_URL=http://127.0.0.1:8001`
- `deploy/n8n-prod.service`: `Environment=AI_ASSISTANT_URL=http://127.0.0.1:8000`

Dodatno `Environment=N8N_BLOCK_ENV_ACCESS_IN_NODE=false` mora biti postavljeno (n8n default-no blokira `$env.*` u expression-ima).

## Logovi

```bash
sudo journalctl -u n8n-staging -f
sudo journalctl -u n8n-prod -f
```

## Why not Docker

Pokušano i odustao zbog Proxmox unprivileged LXC ograničenja:
- `overlay2` storage driver pukao (`userxattr` invalid argument na ZFS subvol)
- `fuse-overlayfs` zahtijeva `/dev/fuse` koji nije passed-through u LXC
- `runc` traži `net.ipv4.ip_unprivileged_port_start` write u read-only `/proc/sys`
- `crun` runtime puca na `cgroup.subtree_control` write (cgroup v2 hierarchy issue u unprivileged LXC)

Native npm install + systemd zaobilazi sve navedeno. n8n je Node app — Node 22 je već na sistemu, install je trivijalan.
