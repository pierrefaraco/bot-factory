"""Per-request DB session scoping for native FastAPI routes.

get_async_session() (see ai_server/database/session.py's own module
docstring) hands out a fresh AsyncSession for the duration of one request
-- or one streamed response body -- released back to the pool when that
unit of work ends.

Wired via Depends (async_db_session_dependency below), not a decorator on
the endpoint function: it's an *async* generator dependency, and FastAPI
resolves those with a plain `await` (fastapi.dependencies.utils.
_solve_generator), in the very same task that then calls the endpoint --
no thread hop, so the contextvar it sets is still visible in the endpoint
body and in everything it awaits. A *sync* generator dependency wouldn't
have this property: FastAPI dispatches it via its own independent
run_in_threadpool() call, and a contextvar set inside that copied,
thrown-away context never makes it back to the request's real one.

Use as `dependencies=[Depends(async_db_session_dependency)]` on the
APIRouter(...) constructor, once per router -- applies to every route
registered on it.
"""

from ai_server.database.session import async_db_session_scope


async def async_db_session_dependency():
    """FastAPI Depends() dependency opening one DB session scope for the
    lifetime of one request. Yields nothing -- it's only entered for its
    open/close side effect."""
    async with async_db_session_scope():
        yield


async def stream_with_async_db_session(async_iterator):
    """DB session scoping for a StreamingResponse body, one level deeper
    than async_db_session_dependency above: rag_svc.py's SSE generators do
    a DB write on their very last step (saving the assistant's reply)
    *during* StreamingResponse's iteration of the body -- i.e. after the
    endpoint function has already returned and async_db_session_dependency
    has already closed its own scope for this request.

    A single scope opened once here, around the whole generator, is
    enough (no per-chunk push/pop needed): starlette.responses.
    StreamingResponse stores an async iterable as-is and drives it with a
    plain `async for`, entirely within the one task already handling this
    request (see its own __init__/stream_response) -- unlike a *sync*
    iterator, which only reaches StreamingResponse via Starlette's
    iterate_in_threadpool, dispatching every single next() call through
    its own independent anyio.to_thread.run_sync() call (a scope entered
    on one such call would be invisible on the next).
    """
    async with async_db_session_scope():
        async for chunk in async_iterator:
            yield chunk
