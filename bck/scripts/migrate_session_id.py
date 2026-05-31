"""
Migration: dodaj `session_id` kolonu u `requests` tabelu (idempotentno).

Pokreni jednom poslije pull-a sa session feature granom:
  python scripts/migrate_session_id.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.storage.db import get_engine  # noqa: E402


async def _main() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        # Provjeri da li kolona već postoji
        rows = (await conn.execute(text("PRAGMA table_info(requests)"))).fetchall()
        col_names = {r[1] for r in rows}
        if "session_id" in col_names:
            print("✅ session_id kolona već postoji — nothing to do")
            return

        await conn.execute(text(
            "ALTER TABLE requests ADD COLUMN session_id VARCHAR(36)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_requests_session_id "
            "ON requests(session_id)"
        ))
        print("✅ Dodato session_id + index")


if __name__ == "__main__":
    asyncio.run(_main())
