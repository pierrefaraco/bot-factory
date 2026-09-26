"""Engines and per-request session scoping (sync + async).

ORM models live in ai_server/models/; this module knows nothing about
them. Base.query (the Model.query compat property) is attached in
models/base.py.
"""

import contextvars
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import scoped_session, sessionmaker

from ai_server.config.config import AppConfig

# Flask-SQLAlchemy previously backed Model.query/db.session with a
# scoped_session tied to Flask's own app-context contextvar, torn down
# automatically when that context popped. Every route is now native
# FastAPI, so this scopes the same way but on a contextvar this module
# owns directly instead: db_session_scope() (used by
# ai_server/dependencies/db_session.py's async_db_session_dependency /
# stream_with_async_db_session) sets it to a fresh, unique value for one
# request -- or one streamed chunk, for a long-lived streaming response --
# and calls SessionLocal.remove() when that unit of work ends, so a
# Session never survives past the request that created it, same lifecycle
# as before without needing a Flask app context to provide it.
_db_scope_id = contextvars.ContextVar("db_scope_id", default=None)


def _scopefunc():
    return _db_scope_id.get()


_engine = None


def _get_engine():
    # Lazy: Flask-SQLAlchemy didn't build its engine until db.init_app(app)
    # ran against a real app's already-loaded config, so importing this
    # module on its own (e.g. test/factories.py, for the model classes)
    # never required DATABASE_URL to be set. create_engine(None) fails
    # immediately (invalid URL), so building it eagerly at import time here
    # would newly require every such import to have DATABASE_URL set too --
    # deferring to first actual use preserves the original laziness.
    global _engine
    if _engine is None:
        _engine = create_engine(AppConfig.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
    return _engine


def _session_factory():
    return sessionmaker(bind=_get_engine())()


SessionLocal = scoped_session(_session_factory, scopefunc=_scopefunc)


@contextmanager
def db_session_scope():
    token = _db_scope_id.set(object())
    try:
        yield
    finally:
        SessionLocal.remove()
        _db_scope_id.reset(token)


class _DbCompat:
    """Minimal flask_sqlalchemy.SQLAlchemy drop-in exposing only what this
    codebase's db.session call sites actually use, so none of them need to
    change. (Models subclass models.base.Base directly.)"""

    session = SessionLocal

db = _DbCompat()


# ===== Async SQLAlchemy (incremental migration -- see
# /root/.claude/plans/moonlit-leaping-salamander.md) =====
#
# Coexists with the sync engine/session above; nothing sync is removed or
# changed by this. Migrated async services call get_async_session() instead
# of `db.session`, inside a request scoped by
# dependencies/db_session.py::async_db_session_dependency (a FastAPI
# Depends()). There is no async equivalent of Model.query
# (scoped_session.query_property() has no AsyncSession analogue), so async
# call sites use SQLAlchemy 2.0's own idiomatic style instead:
# `await session.execute(select(Model).filter_by(...))`.
#
# async_scoped_session mirrors the sync scoped_session above as closely as
# SQLAlchemy allows: same contextvar-scoping idea (a fresh scope per
# request, torn down via .remove() when the request ends), just async.
_async_db_scope_id = contextvars.ContextVar("async_db_scope_id", default=None)


def _async_scopefunc():
    return _async_db_scope_id.get()


_async_engine = None


def _get_async_engine():
    # Lazy for the same reason as _get_engine() above: importing this module
    # (e.g. for the model classes) must not require DATABASE_URL to be set.
    global _async_engine
    if _async_engine is None:
        if "+pymysql" not in AppConfig.SQLALCHEMY_DATABASE_URI:
            raise RuntimeError(
                "DATABASE_URL is not a mysql+pymysql:// URL -- can't derive "
                "the mysql+asyncmy:// async URL from it. "
                f"Got: {AppConfig.SQLALCHEMY_DATABASE_URI!r}"
            )
        async_url = AppConfig.SQLALCHEMY_DATABASE_URI.replace(
            "+pymysql", "+asyncmy", 1
        )
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
    """Current request's AsyncSession -- the async counterpart of `db.session`.

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
