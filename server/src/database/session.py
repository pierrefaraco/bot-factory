"""Async engine and per-request session scoping.

ORM models live in src/models/; this module knows nothing about
them. Every DB access goes through get_async_session() (via the
repositories, see src/repositories/), inside a request scoped by
dependencies/db_session.py::async_db_session_dependency (a FastAPI
Depends()) -- or async_db_session_scope() directly outside a request
(e.g. asgi.py's startup).

async_scoped_session keys the session on a contextvar this module owns:
async_db_session_scope() sets it to a fresh, unique value for one unit of
work and calls .remove() when that unit of work ends, so a session never
survives past the request that created it.
"""

import contextvars
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from src.config.config import AppConfig

_async_db_scope_id = contextvars.ContextVar("async_db_scope_id", default=None)


def _async_scopefunc():
    return _async_db_scope_id.get()


_async_engine = None


def _get_async_engine():
    # Lazy: importing this module (e.g. via the model classes, from
    # test/factories.py or Alembic) must not require DATABASE_URL to be set.
    global _async_engine
    if _async_engine is None:
        if "+pymysql" not in AppConfig.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError(
                "DATABASE_URL is not a mysql+pymysql:// URL -- can't derive "
                "the mysql+asyncmy:// async URL from it. "
                f"Got: {AppConfig.SQLALCHEMY_DATABASE_URI!r}"
            )
        async_url = AppConfig.SQLALCHEMY_DATABASE_URI.replace("+pymysql", "+asyncmy", 1)
        _async_engine = create_async_engine(async_url, pool_pre_ping=True)
    return _async_engine


def _async_session_factory():
    return async_sessionmaker(bind=_get_async_engine(), expire_on_commit=False)()


AsyncSessionLocal = async_scoped_session(
    _async_session_factory, scopefunc=_async_scopefunc
)


@asynccontextmanager
async def async_db_session_scope():
    token = _async_db_scope_id.set(object())
    try:
        yield
    finally:
        await AsyncSessionLocal.remove()
        _async_db_scope_id.reset(token)


def get_async_session() -> AsyncSession:
    """Current request's AsyncSession.

    Must be called from inside async_db_session_scope() (i.e. a request
    scoped by dependencies.db_session.async_db_session_dependency): raises
    instead of silently opening an unscoped session that would never get
    torn down."""
    if _async_db_scope_id.get() is None:
        raise RuntimeError(
            "get_async_session() called outside async_db_session_scope() -- "
            "make sure the router declares "
            "dependencies=[Depends(async_db_session_dependency)]"
        )
    return AsyncSessionLocal()
