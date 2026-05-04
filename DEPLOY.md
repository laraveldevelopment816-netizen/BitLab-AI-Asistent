# Deploy

Server konvencije: [`DEPLOY_GUIDE.md`](./DEPLOY_GUIDE.md).
Sledeći korak: automatizacija kroz `scripts/deploy.sh` + CI git runner.

```bash
# Release folder + clone
RELEASE=$(date +%Y%m%d_%H%M)

mkdir -p /home/ai/aiasistent-prod/releases/$RELEASE

git clone -b production-prep git@github.com:laraveldevelopment816-netizen/BitLab-AI-Asistent.git /home/ai/aiasistent-prod/releases/$RELEASE

cd /home/ai/aiasistent-prod/releases/$RELEASE

# Python venv + deps (CPU torch obavezan)
python3 -m venv .venv

source .venv/bin/activate

pip install -e . --extra-index-url https://download.pytorch.org/whl/cpu

# Symlinks na shared resources (preživljavaju releaseve)
ln -sfn /home/ai/aiasistent-prod/shared/.env .env

ln -sfn /home/ai/aiasistent-prod/shared/var var

# Index — SAMO prvi put (~5min CPU, ~5GB temp diska); preskoči ako postoji
python scripts/embed_products.py

mv data/products.index.npz data/products.meta.json var/

# Symlinkuj index iz shared/var u release data/
ln -sfn $(pwd)/var/products.index.npz data/products.index.npz

ln -sfn $(pwd)/var/products.meta.json data/products.meta.json

# Kategorije + DB schema (deterministički, brzo)
python scripts/build_categories.py

python scripts/init_db.py

# Dashboard SPA build (Vite → dashboard/dist/)
cd dashboard

pnpm install --frozen-lockfile

pnpm build

cd ..

# Atomic switch
ln -sfn /home/ai/aiasistent-prod/releases/$RELEASE /home/ai/aiasistent-prod/current

# Restart
sudo systemctl restart aiasistent-prod
```

Prvi put: kopiraj `deploy/bitlab-ai.service` i `deploy/nginx-site.conf`, popuni `shared/.env`, Node 22, certbot.
Rollback: `ln -sfn` na stari release + `sudo systemctl restart aiasistent-prod`.
