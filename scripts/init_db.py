"""
Idempotentno kreiraj tabele dashboard storage-a.
Pokreni: python scripts/init_db.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.storage.db import init_db, _db_url  # noqa: E402


async def _main() -> None:
    print(f"Inicijalizujem schema na: {_db_url()}")
    await init_db()
    print("✅ Tabele kreirane (requests, tool_calls).")


if __name__ == "__main__":
    asyncio.run(_main())
