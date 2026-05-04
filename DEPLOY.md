# Deploy — 8 komandi

```bash
# 1. Release folder + clone
RELEASE=$(date +%Y%m%d_%H%M)
mkdir -p /home/ai/aiasistent-staging/releases/$RELEASE
git clone -b production-prep git@github.com:laraveldevelopment816-netizen/BitLab-AI-Asistent.git \
  /home/ai/aiasistent-staging/releases/$RELEASE
cd /home/ai/aiasistent-staging/releases/$RELEASE

# 2. Python deps (CPU torch obavezno)
python3 -m venv .venv && source .venv/bin/activate
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu

# 3. Shared resources (.env + var preživi releaseve)
ln -sfn /home/ai/aiasistent-staging/shared/.env .env
ln -sfn /home/ai/aiasistent-staging/shared/var  var

# 4. Data (samo prvi put — index regen traje ~5min)
[ -f var/products.index.npz ] || {
  python scripts/embed_products.py
  mv data/products.index.npz data/products.meta.json var/
}
ln -sfn $(pwd)/var/products.index.npz data/products.index.npz
ln -sfn $(pwd)/var/products.meta.json data/products.meta.json
python scripts/build_categories.py
python scripts/init_db.py

# 5. Dashboard build
cd dashboard && pnpm install --frozen-lockfile && pnpm build && cd ..

# 6. Atomic switch
ln -sfn /home/ai/aiasistent-staging/releases/$RELEASE /home/ai/aiasistent-staging/current

# 7. Restart
sudo systemctl restart aiasistent-staging

# 8. Smoke
curl -fsS https://staging.aiasistent.bitlab.rs/healthz
```

---

## Prvi put (jednom postaviš, više ne diraš)

```bash
# .env (popuni ručno)
mkdir -p /home/ai/aiasistent-staging/{releases,shared/{var,logs}}
nano /home/ai/aiasistent-staging/shared/.env

# Systemd unit
sudo cp deploy/bitlab-ai.service /etc/systemd/system/aiasistent-staging.service
sudo sed -i 's/bitlab-ai/aiasistent-staging/g; s|/opt/bitlab-ai|/home/ai/aiasistent-staging/current|g; s/User=bitlab/User=ai/; s/Group=bitlab/Group=ai/' \
  /etc/systemd/system/aiasistent-staging.service
sudo systemctl daemon-reload && sudo systemctl enable aiasistent-staging

# Nginx
sudo cp deploy/nginx-site.conf /etc/nginx/hosts/aiasistent-staging.conf
sudo sed -i 's/AI_DOMAIN_PLACEHOLDER/staging.aiasistent.bitlab.rs/g' /etc/nginx/hosts/aiasistent-staging.conf
sudo nginx -t && sudo systemctl reload nginx

# SSL
sudo certbot --nginx -d staging.aiasistent.bitlab.rs --non-interactive --agree-tos --email bjovkovic@gmail.com --redirect
```

---

## Rollback

```bash
ls /home/ai/aiasistent-staging/releases/
ln -sfn /home/ai/aiasistent-staging/releases/<TIMESTAMP> /home/ai/aiasistent-staging/current
sudo systemctl restart aiasistent-staging
```

---

## Reference (samo ako pukne)

`SERVER-DEPLOY-PLAN.md` — verbose detalji, troubleshooting, varijante.
`DEPLOY_GUIDE.md` — server konvencije od Ivana (Pattern A, port mapa).
`README.md` Sekcija 10 — pregled.
