#!/bin/bash
# Automatsko osvježavanje kataloga — pokreće se cron jobom.
# Crontab: 0 3 * * * /opt/bitlab-ai-asistent/scripts/refresh_index.sh >> /var/log/bitlab-refresh.log 2>&1
set -e

PROJECT="/opt/bitlab-ai-asistent"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Počinjem osvježavanje kataloga..."

cd "$PROJECT"
source .venv/bin/activate

# Korak 1: Povuci svježe podatke iz MySQL
# Alternativa: zakomentiraj ovo i ručno SCPuj all-products.json
python scripts/pull_from_mysql.py

# Korak 2: Generiši embedding indeks
python scripts/embed_products.py

# Korak 3: Restartuj FastAPI servis da učita novi indeks
systemctl restart bitlab-ai

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gotovo. Katalog osvježen i servis restartovan."
