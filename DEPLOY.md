# Deploy

```bash
RELEASE=$(date +%Y%m%d_%H%M)
mkdir -p /home/ai/aiasistent-staging/releases/$RELEASE
git clone -b production-prep git@github.com:laraveldevelopment816-netizen/BitLab-AI-Asistent.git /home/ai/aiasistent-staging/releases/$RELEASE
cd /home/ai/aiasistent-staging/releases/$RELEASE
python3 -m venv .venv && source .venv/bin/activate
pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu
ln -sfn /home/ai/aiasistent-staging/shared/.env .env && ln -sfn /home/ai/aiasistent-staging/shared/var var
[ -f var/products.index.npz ] || { python scripts/embed_products.py; mv data/products.index.npz data/products.meta.json var/; }
ln -sfn $(pwd)/var/products.index.npz data/products.index.npz && ln -sfn $(pwd)/var/products.meta.json data/products.meta.json
python scripts/build_categories.py && python scripts/init_db.py
cd dashboard && pnpm install --frozen-lockfile && pnpm build && cd ..
ln -sfn /home/ai/aiasistent-staging/releases/$RELEASE /home/ai/aiasistent-staging/current
sudo systemctl restart aiasistent-staging
```

Server konvencije: [`DEPLOY_GUIDE.md`](./DEPLOY_GUIDE.md). Prvi put: kopiraj `deploy/bitlab-ai.service` i `deploy/nginx-site.conf`, popuni `shared/.env`, Node 22, certbot. Rollback: `ln -sfn` na stari release + `systemctl restart`.
