"""
Async SQLAlchemy engine + sessionmaker za logging dashboard.
Default DB: var/bitlab.db (relativno na project root).
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DB = PROJECT_ROOT / "var" / "bitlab.db"

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _db_url() -> str:
    raw = os.getenv("DASHBOARD_DB_URL")
    if raw:
        return raw if "://" in raw else f"sqlite+aiosqlite:///{raw}"
    _DEFAULT_DB.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{_DEFAULT_DB}"


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(_db_url(), echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db() -> None:
    """Idempotentno kreiraj tabele ako ne postoje."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
