"""
Povlači tabelu 'products' direktno iz webshop MySQL baze
i upisuje data/all-products.json u istom formatu kao phpMyAdmin export.

Zavisnost (instaliraj jednom):
    pip install pymysql

.env varijable (dodaj u .env):
    MYSQL_HOST=IP-ADRESA-WEBSHOP-SERVERA
    MYSQL_PORT=3306
    MYSQL_USER=webshop_user
    MYSQL_PASSWORD=lozinka
    MYSQL_DB=webshop_baza

Pokretanje:
    python scripts/pull_from_mysql.py
    python scripts/embed_products.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.config import settings  # noqa: E402


def main() -> None:
    try:
        import pymysql
        import pymysql.cursors
    except ImportError:
        print("GREŠKA: pymysql nije instaliran. Pokreni: pip install pymysql", file=sys.stderr)
        sys.exit(1)

    host     = os.environ.get("MYSQL_HOST", "").strip()
    port     = int(os.environ.get("MYSQL_PORT", "3306"))
    user     = os.environ.get("MYSQL_USER", "").strip()
    password = os.environ.get("MYSQL_PASSWORD", "").strip()
    db       = os.environ.get("MYSQL_DB", "").strip()

    missing = [k for k, v in [
        ("MYSQL_HOST", host), ("MYSQL_USER", user),
        ("MYSQL_PASSWORD", password), ("MYSQL_DB", db),
    ] if not v]

    if missing:
        print(f"GREŠKA: Postavi u .env: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    print(f"→ Spajam se na {host}:{port}/{db} ...")
    try:
        conn = pymysql.connect(
            host=host, port=port, user=user, password=password,
            database=db, cursorclass=pymysql.cursors.DictCursor,
            charset="utf8mb4", connect_timeout=10,
        )
    except pymysql.err.OperationalError as exc:
        print(f"GREŠKA: Konekcija odbijena — {exc}", file=sys.stderr)
        print("  Provjeri: MYSQL_HOST, port 3306, korisničke privilegije, firewall.", file=sys.stderr)
        sys.exit(1)

    with conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM products")
            rows = cur.fetchall()

    print(f"  Pronađeno {len(rows)} redova u tabeli 'products'.")

    # phpMyAdmin format koji embed_products.py očekuje
    export = [{"type": "table", "name": "products", "data": rows}]

    out_path = settings.products_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(export, ensure_ascii=False, default=str, indent=2),
        encoding="utf-8",
    )
    size_mb = out_path.stat().st_size / 1_048_576
    print(f"✓ Sačuvano: {out_path} ({size_mb:.1f} MB)")
    print("\nSad pokreni:")
    print("    python scripts/embed_products.py")


if __name__ == "__main__":
    main()
