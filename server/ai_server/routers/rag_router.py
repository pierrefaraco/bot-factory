"""RAG (Retrieval-Augmented Generation) REST API -- native FastAPI port of
the former ai_server/rest/rest_rag.py Flask blueprint (Phase 8 of the
Flask -> FastAPI migration; rest_authent.py is the one remaining
blueprint after this). Same URLs, same response shapes, same
role/ownership checks.

Every route here is `async def`: this is the "dedicated RAG-phase pass"
bot_svc.py's delete() previously deferred to, covering rag_svc.py,
message_svc.py and the handful of bot_svc/bot_assignment_svc/
bot_parameters_svc lookups this router needs -- transmit_to_alfred
included, its one still-fully-sync call (knowledge_svc.
recordChaptersToVectorDB, see its own docstring) pushed onto
run_in_threadpool rather than left as a sync `def` route. Genuinely
blocking, non-DB-async work with no async equivalent (ChromaDB, the LLM's
own retriever step) is pushed onto FastAPI's threadpool explicitly via
run_in_threadpool from inside rag_svc.py/knowledge_svc.py, or -- for the
retriever, invoked from deep inside the LCEL chain -- picked up
automatically by LangChain's own executor-offloading default for a sync
RunnableLambda under .ainvoke()/.astream().

DB session scoping uses no decorator at all: since every route is `async
def`, the router declares `dependencies=[Depends(async_db_session_dependency)]`
once, applying it to every path operation -- see
dependencies/db_session.py's module docstring for why an async-generator
Depends is safe here (no thread hop between it and the endpoint call)
where it wouldn't be for a sync `def` route.

Streaming (trigfirstmessage?stream=TRUE, streamchat): rag_svc.py's
ask_with_stream() returns an *async* generator now (rag_chain.astream()
instead of .stream()), which changes how the per-chunk DB scope has to
work. A sync generator only reaches StreamingResponse via Starlette's
iterate_in_threadpool, which dispatches every next() call through its own
independent threadpool call -- a scope entered on one such call is
invisible on the next regardless of when the endpoint function itself
returns, which is why the old sync path needed dependencies.db_session.
stream_with_db_session to push/pop a fresh scope around every single
next(). An async generator gets no such treatment: StreamingResponse
drives it with a plain `async for`, directly on the one task already
handling this request (see starlette.responses.StreamingResponse), so
dependencies.db_session.stream_with_async_db_session only needs to open
the scope once, around the whole generator -- it naturally stays entered
across every `yield`.

The original had no @api.validate on either streaming route specifically
because SpecTree's Flask integration drains a streamed Response into
memory via response.get_data() before Werkzeug can stream it (see the
git history on rest_rag.py) -- moot here since there's no SpecTree
layer for native routes at all.

The manual `Access-Control-Allow-Origin: "*"` header the original set
directly on these two Response objects is dropped: asgi.py's
CORSMiddleware now adds that header to every response uniformly (see
its own module docstring), so keeping both would emit two ACAO headers
on a stream response instead of one.
"""

import json
import time
from typing import Callable

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dependencies.auth import require_roles
from ai_server.dependencies.content_type import require_json_body
from ai_server.dependencies.db_session import (
    async_db_session_dependency,
    stream_with_async_db_session,
)
from ai_server.dependencies.services import (
    BotAssignmentServiceDep,
    BotParametersServiceDep,
    BotServiceDep,
    KnowledgeServiceDep,
    MessageServiceDep,
    RagServiceDep,
    TokenTrackingServiceDep,
    UserAdminServiceDep,
)
from ai_server.dto.user_dto import UserDto
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.bot_assignment_svc import BotAssignmentService
from ai_server.services.bot_svc import BotService
from ai_server.services.message_svc import MessageService
from ai_server.services.token_tracking_svc import TokenTrackingService

router = APIRouter(
    prefix="/api/rag",
    tags=["rag"],
    dependencies=[Depends(async_db_session_dependency)],
)

logger = BotFactoryLogger()

any_role = require_roles([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
admin_or_user = require_roles([ADMIN_ROLE, USER_ROLE])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class ChatRequest(BaseModel):
    """Schema for chat validation"""

    question: str = Field(min_length=1)


async def _check_bot_access_permission(
    user: UserDto,
    bot_id: int,
    bot_assignment_svc: BotAssignmentService,
    bot_svc: BotService,
) -> bool:
    if user.roles == ADMIN_ROLE:
        return True
    elif user.roles == USER_ROLE:
        return await bot_svc.is_bot_belong_to_user_async(bot_id, user.id)
    elif user.roles == GUEST_ROLE:
        return await bot_assignment_svc.is_bot_assigned_to_user(bot_id, user.id)
    return False


async def _enforce_token_quota(
    user: UserDto, token_tracking_svc: TokenTrackingService
) -> None:
    """Refuse the request with a 429 once the user's billed account has
    reached TOKEN_LIMIT_PER_USER_24H (see TokenTrackingService.get_token_quota).
    Checked before the LLM call, so the request that crosses the limit is
    still served in full: this is a soft cap, not an exact one."""
    quota = await token_tracking_svc.get_token_quota(user)
    if quota["exceeded"]:
        logger.warning(
            f"LLM call rejected: user {user.id} (billed to {quota['billed_user_id']}) "
            f"used {quota['used_24h']}/{quota['limit_24h']} tokens in the last 24h"
        )
        raise ApiError(
            f"Token limit reached ({quota['limit_24h']} tokens per 24h). Please try again later.",
            status_code=429,
        )


@router.post("/chat", dependencies=[Depends(require_json_body(ChatRequest))])
async def chat(
    body: ChatRequest,
    rag_svc: RagServiceDep,
    user_svc: UserAdminServiceDep,
    bot_assignment_svc: BotAssignmentServiceDep,
    bot_svc: BotServiceDep,
    token_tracking_svc: TokenTrackingServiceDep,
    claims: dict = Depends(any_role),
):
    """Basic chat endpoint"""
    logger.info("POST /rag/chat - chat called")
    user_id = claims["sub"]
    user = await user_svc.get_user_dto_by_id(user_id)
    if not user:
        logger.warning(f"chat rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    selected_bot_id = user.selected_bot_id
    if not selected_bot_id:
        logger.warning(f"chat rejected: user {user_id} has no selected bot")
        raise ApiError("You have to select a bot on the app", status_code=409)

    if not await _check_bot_access_permission(
        user, selected_bot_id, bot_assignment_svc, bot_svc
    ):
        logger.warning(f"chat forbidden: user {user_id} has no access to bot {selected_bot_id}")
        raise ApiError(f"You don't have permission to access bot {selected_bot_id}", status_code=403)

    await _enforce_token_quota(user, token_tracking_svc)

    started_at = time.perf_counter()
    response = await rag_svc.ask(selected_bot_id, user_id, body.question)
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        f"chat succeeded for user_id={user_id} bot_id={selected_bot_id} elapsed_ms={elapsed_ms:.1f}"
    )
    return {"response": response}


@router.get("/trigfirstmessage")
async def trigfirstmessage(
    rag_svc: RagServiceDep,
    user_svc: UserAdminServiceDep,
    bot_parameters_svc: BotParametersServiceDep,
    message_service: MessageServiceDep,
    bot_assignment_svc: BotAssignmentServiceDep,
    bot_svc: BotServiceDep,
    token_tracking_svc: TokenTrackingServiceDep,
    claims: dict = Depends(any_role),
    stream: str = Query(default="TRUE"),
    data: str = Query(default="{}"),
):
    """Trigger first welcome message for a bot"""
    logger.info("GET /rag/trigfirstmessage - trigfirstmessage called")
    user_id = claims["sub"]
    user = await user_svc.get_user_dto_by_id(user_id)
    if not user:
        logger.warning(f"trigfirstmessage rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    bot_id = user.selected_bot_id
    if not bot_id:
        logger.warning(f"trigfirstmessage rejected: user {user_id} has no selected bot")
        raise ApiError("Bot_id is required", status_code=400)

    try:
        bot_id = int(bot_id)
    except ValueError:
        logger.warning(f"trigfirstmessage rejected: invalid bot_id format {bot_id!r}")
        raise ApiError("Invalid bot_id format", status_code=400)

    if not await _check_bot_access_permission(
        user, bot_id, bot_assignment_svc, bot_svc
    ):
        logger.warning(f"trigfirstmessage forbidden: user {user_id} has no access to bot {bot_id}")
        raise ApiError(f"You don't have permission to access bot {bot_id}", status_code=403)

    await _enforce_token_quota(user, token_tracking_svc)

    question = await bot_parameters_svc.get_welcome_message(user.name, bot_id)
    stream_response = stream.upper() == "TRUE"
    logger.debug(f"trigfirstmessage params: bot_id={bot_id} stream={stream_response}")

    if stream_response:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("trigfirstmessage rejected: invalid JSON in data parameter")
            raise ApiError("Invalid JSON in data parameter", status_code=400)

        session = await message_service.get_session(bot_id, user_id)
        generate: Callable = await rag_svc.ask_with_stream(
            bot_id, user_id, parsed_data, question, hide=True,
            session_id=session.id if session else -1,
        )
        response_iterator = generate()

        logger.info(f"trigfirstmessage streaming started for user_id={user_id} bot_id={bot_id}")
        return StreamingResponse(
            stream_with_async_db_session(response_iterator),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )
    else:
        await _delete_session_history(bot_id, user_id, message_service)
        started_at = time.perf_counter()
        response = await rag_svc.ask(bot_id, user_id, question, hide=True)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            f"trigfirstmessage succeeded for user_id={user_id} bot_id={bot_id} elapsed_ms={elapsed_ms:.1f}"
        )
        return {"response": response}


@router.get("/streamchat")
async def streamchat(
    rag_svc: RagServiceDep,
    user_svc: UserAdminServiceDep,
    message_service: MessageServiceDep,
    bot_assignment_svc: BotAssignmentServiceDep,
    bot_svc: BotServiceDep,
    token_tracking_svc: TokenTrackingServiceDep,
    claims: dict = Depends(any_role),
    question: str = Query(default=None),
    bot_id: str = Query(default=None),
    data: str = Query(default="{}"),
):
    """Stream chat endpoint with real-time responses"""
    logger.info("GET /rag/streamchat - streamchat called")
    user_id = claims["sub"]
    user = await user_svc.get_user_dto_by_id(user_id)
    if not user:
        logger.warning(f"streamchat rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    if not question or not question.strip():
        logger.warning(f"streamchat rejected: missing question for user {user_id}")
        raise ApiError("Question parameter is required", status_code=400)
    if not bot_id:
        logger.warning(f"streamchat rejected: missing bot_id for user {user_id}")
        raise ApiError("Bot_id is required", status_code=400)

    try:
        bot_id = int(bot_id)
    except ValueError:
        logger.warning(f"streamchat rejected: invalid bot_id format {bot_id!r}")
        raise ApiError("Invalid bot_id format", status_code=400)

    if not await _check_bot_access_permission(
        user, bot_id, bot_assignment_svc, bot_svc
    ):
        logger.warning(f"streamchat forbidden: user {user_id} has no access to bot {bot_id}")
        raise ApiError(f"You don't have permission to access bot {bot_id}", status_code=403)

    await _enforce_token_quota(user, token_tracking_svc)

    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning("streamchat rejected: invalid JSON in data parameter")
        raise ApiError("Invalid JSON in data parameter", status_code=400)

    logger.debug(f"streamchat question length={len(question)}")
    session = await message_service.get_session(bot_id, user_id)
    generate: Callable = await rag_svc.ask_with_stream(
        bot_id, user_id, parsed_data, question, session_id=session.id if session else -1
    )
    response_iterator = generate()

    logger.info(f"streamchat streaming started for user_id={user_id} bot_id={bot_id}")
    return StreamingResponse(
        stream_with_async_db_session(response_iterator),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/transmit_to_alfred/{bot_id:int}")
async def transmit_to_alfred(
    bot_id: int,
    knowledge_svc: KnowledgeServiceDep,
    claims: dict = Depends(admin_or_user),
):
    """Transmit chapters to vector database.

    knowledge_svc.recordChaptersToVectorDB() itself stays fully sync: it
    re-fetches each Knowledge row and then mutates+commits it
    (vector_synced_at) via the plain sync `db.session` from inside the
    same call (see knowledge_svc.py::_ingest_knowledge_node) while also
    driving ChromaDB writes that have no async client at all
    (chroma_db_svc.py) -- fetching those rows async instead would hand
    back objects bound to a different session than the one the commit
    runs on, silently losing that write. Same class of blocker as
    BotService.delete's own "Left for a dedicated RAG-phase pass" note.
    Run via run_in_threadpool so this route can still be `async def` like
    every other one in this router (and share its Depends-based session
    scoping) without blocking the event loop for the call's duration."""
    logger.info(f"POST /rag/transmit_to_alfred/{bot_id} - transmit_to_alfred called")
    user_id = claims["sub"]
    logger.info(f"User {user_id} transmitting chapters for bot {bot_id} to vector DB")

    started_at = time.perf_counter()
    await run_in_threadpool(knowledge_svc.recordChaptersToVectorDB, bot_id)
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    logger.info(f"transmit_to_alfred succeeded for bot_id={bot_id} elapsed_ms={elapsed_ms:.1f}")
    return {"message": "Chapters transmitted to Alfred successfully"}


@router.get("/{bot_id:int}")
async def get_session_history(
    bot_id: int,
    message_service: MessageServiceDep,
    claims: dict = Depends(any_role),
):
    """Get session history for a bot"""
    logger.info(f"GET /rag/{bot_id} - get_session_history called")
    user_id = claims["sub"]
    session = await message_service.get_session(bot_id, user_id)
    if session is None:
        logger.info(f"get_session_history({bot_id}) no session")
        return Response(status_code=204)
    messages = await message_service.load_session_history(session_id=session.id)
    if not messages:
        logger.info(f"get_session_history({bot_id}) no messages")
        return Response(status_code=204)

    logger.info(f"get_session_history({bot_id}) succeeded count={len(messages)}")
    return [msg.to_dict() for msg in messages]


@router.delete("")
async def delete_selected_bot_session_history(
    user_svc: UserAdminServiceDep,
    message_service: MessageServiceDep,
    claims: dict = Depends(any_role),
):
    """Delete session history for the selected bot"""
    logger.info("DELETE /rag - delete_selected_bot_session_history called")
    user_id = claims["sub"]
    user = await user_svc.get_user_dto_by_id(user_id)
    if not user:
        logger.warning(f"delete_selected_bot_session_history rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    bot_id = user.selected_bot_id
    if not bot_id:
        logger.warning(f"delete_selected_bot_session_history rejected: user {user_id} has no selected bot")
        raise ApiError("Bot_id is required", status_code=400)

    return await _delete_session_history(int(bot_id), user_id, message_service)


@router.delete("/{bot_id:int}")
async def delete_session_history(
    bot_id: int,
    message_service: MessageServiceDep,
    claims: dict = Depends(any_role),
):
    """Delete session history for a bot"""
    logger.info(f"DELETE /rag/{bot_id} - delete_session_history called")
    return await _delete_session_history(bot_id, claims["sub"], message_service)


async def _delete_session_history(
    bot_id: int, user_id, message_service: MessageService
):
    logger.info(f"User {user_id} deleting session history for bot {bot_id}")
    session = await message_service.get_session(bot_id, user_id)
    if session is None:
        logger.info(f"_delete_session_history({bot_id}) no session")
        return {"deleted_message_count": 0}

    deleted_message_count = await message_service.delete_session_history(session.id)
    logger.info(f"_delete_session_history({bot_id}) succeeded deleted_message_count={deleted_message_count}")
    return {"deleted_message_count": deleted_message_count}
