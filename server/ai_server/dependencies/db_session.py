"""Per-request DB session scoping for native FastAPI routes.

Model.query/db.session (see ai_server/database/session.py's own module
docstring) get a fresh SQLAlchemy Session for the duration of one
request -- or one streamed chunk, for a long-lived streaming response --
released back to the pool when that unit of work ends.

Wired via Depends (async_db_session_dependency below), not a decorator on
the endpoint function: it's an *async* generator dependency, and FastAPI
resolves those with a plain `await` (fastapi.dependencies.utils.
_solve_generator), in the very same task that then calls the endpoint --
no thread hop, so a contextvar set there is still visible in the endpoint
body, whether that endpoint is itself `async def` (called directly, same
task) or plain `def` (FastAPI's own separate run_in_threadpool() call for
it still copies the *current* context -- i.e. already carrying whatever
this dependency set -- into that thread; verified empirically against a
throwaway FastAPI app with both an async and a sync route). A *sync*
generator dependency wouldn't have this property: FastAPI dispatches it
via its own independent run_in_threadpool() call, and a contextvar set
inside that copied, thrown-away context never makes it back to the
request's real one -- which is why this dependency is written as an
async generator even though it's used by routers with sync `def` routes
too (avatar_router.py, knowledge_router.py, ...).

Use as `dependencies=[Depends(async_db_session_dependency)]` on the
APIRouter(...) constructor, once per router -- applies to every route
registered on it, sync or async alike.

(This module used to also push a Flask app context here -- needed only
by authent_svc.py/google_authent_svc.py's create_access_token() calls,
which read JWT_SECRET_KEY etc. off current_app.config. Those now read
AppConfig directly instead -- see ai_server/dependencies/auth.py -- so
there's no Flask app left anywhere in the process to push a context for.)
"""

from ai_server.database.session import async_db_session_scope, db_session_scope


async def async_db_session_dependency():
    """FastAPI Depends() dependency opening one DB session scope (sync
    `db_session_scope()` + async `async_db_session_scope()`) for the
    lifetime of one request. Yields nothing -- it's only entered for its
    open/close side effect. See the module docstring for why an
    async-generator dependency is safe here regardless of whether the
    route it's applied to is `async def` or plain `def`."""
    with db_session_scope():
        async with async_db_session_scope():
            yield


async def stream_with_async_db_session(async_iterator):
    """DB session scoping for a StreamingResponse body, one level deeper
    than async_db_session_dependency above: rag_svc.py's SSE generators do
    a DB write on their very last step (saving the assistant's reply)
    *during* StreamingResponse's iteration of the body -- i.e. after the
    endpoint function has already returned and async_db_session_dependency
    has already closed its own scope for this request.

    Only the async scope, unlike async_db_session_dependency: everything
    that runs inside this generator (rag_chain.astream(), message_svc.py's
    save_message, and llm_svc.py's TokenCountingCallback -- now an
    AsyncCallbackHandler, see its own docstring) is fully migrated to
    get_async_session(), with no remaining sync Model.query/db.session
    call reachable from here. (async_db_session_dependency itself still
    needs both: KnowledgeSvc/TemplateSvc (knowledge_svc.py,
    template_svc.py) still use the sync session, run through
    run_in_threadpool from knowledge_router.py, rag_router.py and
    BotService.create_random_bot()/delete().)

    A single scope opened once here, around the whole generator, is
    enough (no per-chunk push/pop needed): starlette.responses.
    StreamingResponse stores an async iterable as-is and drives it with a
    plain `async for`, entirely within the one task already handling this
    request (see its own __init__/stream_response) -- unlike a *sync*
    iterator, which only reaches StreamingResponse via Starlette's
    iterate_in_threadpool, dispatching every single next() call through
    its own independent anyio.to_thread.run_sync() call (a scope entered
    on one such call would be invisible on the next). Since every route
    in this codebase now returns an async generator for its streaming
    body, there's no sync counterpart of this function to reach for.
    """
    async with async_db_session_scope():
        async for chunk in async_iterator:
            yield chunk
