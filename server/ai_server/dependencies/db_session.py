"""Per-request DB session scoping for native FastAPI routes.

Model.query/db.session (see ai_server/dao/database.py's own module
docstring) get a fresh SQLAlchemy Session for the duration of one
request -- or one streamed chunk, for a long-lived streaming response --
released back to the pool when that unit of work ends.

This has to wrap the whole endpoint call, not run as a separate `yield`
Depends: FastAPI resolves each sync dependency via its own
run_in_threadpool() call, and anyio copies contextvars into that call
independently of the endpoint function's own run_in_threadpool() call --
a context entered in one such call is invisible to the other, even
though both belong to the same request. Wrapping the endpoint itself
keeps everything entered under it in one call frame.

(This module used to also push a Flask app context here -- needed only
by authent_svc.py/google_authent_svc.py's create_access_token() calls,
which read JWT_SECRET_KEY etc. off current_app.config. Those now read
AppConfig directly instead -- see ai_server/dependencies/auth.py -- so
there's no Flask app left anywhere in the process to push a context for.)
"""

from functools import wraps

from ai_server.dao.database import db_session_scope


def with_db_session(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        with db_session_scope():
            return fn(*args, **kwargs)

    return wrapper


def stream_with_db_session(iterator):
    """Same problem as above, one level deeper: a StreamingResponse's body
    iterator has each of its next() calls dispatched independently via
    Starlette's iterate_in_threadpool (its own anyio.to_thread.run_sync
    per call). rag_svc.py's SSE generators do a DB write on their very
    last step (saving the assistant's reply) *after* the endpoint
    function has already returned the StreamingResponse and its own
    with_db_session has already exited -- and a scope entered during one
    next() call is invisible to the next one regardless, so wrapping the
    whole generator in one `with` (relying on it staying "open" across
    yields) would not actually keep the scope alive by the time that last
    step runs. Push/pop around each individual next() call instead, so
    every step is self-contained the same way with_db_session's single
    call frame is.
    """
    while True:
        with db_session_scope():
            try:
                chunk = next(iterator)
            except StopIteration:
                return
        yield chunk
