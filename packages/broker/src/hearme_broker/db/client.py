"""asyncpg pool lifecycle.

A single module-level pool is created on app startup and torn down on
shutdown. Tests can also call ``init_pool(dsn=...)`` directly.
"""

from __future__ import annotations

import asyncpg

from ..config import get_settings

_pool: asyncpg.Pool | None = None


async def init_pool(dsn: str | None = None) -> asyncpg.Pool:
    """Create the global pool. Idempotent."""
    global _pool
    if _pool is not None:
        return _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        dsn=dsn or settings.database_url,
        min_size=settings.db_pool_min_size,
        max_size=settings.db_pool_max_size,
    )
    return _pool


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized; call init_pool() first")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
