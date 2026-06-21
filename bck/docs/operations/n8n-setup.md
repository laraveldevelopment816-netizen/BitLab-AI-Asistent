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
   - **IMAP** node: koristi `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` iz `aiasistent-staging/shared/.env`
   - **HTTP Request** node: URL = `https://staging.aiasistent.bitlab.rs/api/email`
   - **SMTP** node: `SMTP_*` iz istog `.env`-a
6. Activate workflow (toggle gore desno)

## Nginx + DNS + SSL (TODO za prvi setup)

DNS A record `n8n-staging.bitlab.rs` → server IP. Nginx config u `/etc/nginx/hosts/n8n-staging.conf` proxy na `127.0.0.1:8031` sa websocket headers (`proxy_set_header Upgrade`, `Connection upgrade`). Certbot za SSL.

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
