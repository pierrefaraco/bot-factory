"""RAG (Retrieval-Augmented Generation) REST API -- native FastAPI port of
the former ai_server/rest/rest_rag.py Flask blueprint (Phase 8 of the
Flask -> FastAPI migration; rest_authent.py is the one remaining
blueprint after this). Same URLs, same response shapes, same
role/ownership checks.

Streaming (trigfirstmessage?stream=TRUE, streamchat): rag_svc.py's
generators do a DB write (saving the assistant's reply) on their very
last step, which runs *during* StreamingResponse's iteration of the body
-- i.e. after this endpoint function has already returned and its own
with_db_session has already exited. Starlette also dispatches each
individual next() call on that body iterator through its own
independent threadpool call, so a scope entered on one next() call
isn't visible on another regardless of when the function itself
returns. dependencies.db_session.stream_with_db_session wraps the
generator so every single next() call gets its own self-contained
push/pop, exactly like with_db_session does for the synchronous part
of the request.

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

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dao.database import User
from ai_server.dependencies.auth import require_roles
from ai_server.dependencies.content_type import require_json_body
from ai_server.dependencies.db_session import (
    stream_with_db_session,
    with_db_session,
)
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.bot_assignment_svc import BotAssignmentService
from ai_server.services.bot_parameters_svc import BotParametersService
from ai_server.services.bot_svc import BotService
from ai_server.services.knowledge_svc import KnowledgeSvc
from ai_server.services.rag_svc import RagService, message_service
from ai_server.services.user_admin_svc import UserAdminService

router = APIRouter(prefix="/api/rag", tags=["rag"])

logger = BotFactoryLogger()
rag_svc = RagService()
knowledge_svc = KnowledgeSvc(rag_svc)
bot_assignment_svc = BotAssignmentService()
bot_svc = BotService()
user_svc = UserAdminService()
bot_parameters_svc = BotParametersService()

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


def _check_bot_access_permission(user: User, bot_id: int) -> bool:
    if user.roles == ADMIN_ROLE:
        return True
    elif user.roles == USER_ROLE:
        return bot_svc.is_bot_belong_to_user(bot_id, user.id)
    elif user.roles == GUEST_ROLE:
        return bot_assignment_svc.is_bot_assigned_to_user(bot_id, user.id)
    return False


@router.post("/chat", dependencies=[Depends(require_json_body(ChatRequest))])
@with_db_session
def chat(body: ChatRequest, claims: dict = Depends(any_role)):
    """Basic chat endpoint"""
    logger.info("POST /rag/chat - chat called")
    user_id = claims["sub"]
    user: User = user_svc.get_user_by_id(user_id)
    if not user:
        logger.warning(f"chat rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    selected_bot_id = user.selected_bot_id
    if not selected_bot_id:
        logger.warning(f"chat rejected: user {user_id} has no selected bot")
        raise ApiError("You have to select a bot on the app", status_code=409)

    if not _check_bot_access_permission(user, selected_bot_id):
        logger.warning(f"chat forbidden: user {user_id} has no access to bot {selected_bot_id}")
        raise ApiError(f"You don't have permission to access bot {selected_bot_id}", status_code=403)

    started_at = time.perf_counter()
    response = rag_svc.ask(selected_bot_id, user_id, body.question)
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        f"chat succeeded for user_id={user_id} bot_id={selected_bot_id} elapsed_ms={elapsed_ms:.1f}"
    )
    return {"response": response}


@router.get("/trigfirstmessage")
@with_db_session
def trigfirstmessage(
    claims: dict = Depends(any_role),
    stream: str = Query(default="TRUE"),
    data: str = Query(default="{}"),
):
    """Trigger first welcome message for a bot"""
    logger.info("GET /rag/trigfirstmessage - trigfirstmessage called")
    user_id = claims["sub"]
    user: User = user_svc.get_user_by_id(user_id)
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

    if not _check_bot_access_permission(user, bot_id):
        logger.warning(f"trigfirstmessage forbidden: user {user_id} has no access to bot {bot_id}")
        raise ApiError(f"You don't have permission to access bot {bot_id}", status_code=403)

    question = bot_parameters_svc.get_welcome_message(user.name, bot_id)
    stream_response = stream.upper() == "TRUE"
    logger.debug(f"trigfirstmessage params: bot_id={bot_id} stream={stream_response}")

    if stream_response:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("trigfirstmessage rejected: invalid JSON in data parameter")
            raise ApiError("Invalid JSON in data parameter", status_code=400)

        session = message_service.get_session(bot_id, user_id)
        generate: Callable = rag_svc.ask_with_stream(
            bot_id, user_id, parsed_data, question, hide=True,
            session_id=session.id if session else -1,
        )
        response_iterator = generate(rag_svc)

        logger.info(f"trigfirstmessage streaming started for user_id={user_id} bot_id={bot_id}")
        return StreamingResponse(
            stream_with_db_session(response_iterator),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )
    else:
        _delete_session_history(bot_id, user_id)
        started_at = time.perf_counter()
        response = rag_svc.ask(bot_id, user_id, question, hide=True)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            f"trigfirstmessage succeeded for user_id={user_id} bot_id={bot_id} elapsed_ms={elapsed_ms:.1f}"
        )
        return {"response": response}


@router.get("/streamchat")
@with_db_session
def streamchat(
    claims: dict = Depends(any_role),
    question: str = Query(default=None),
    bot_id: str = Query(default=None),
    data: str = Query(default="{}"),
):
    """Stream chat endpoint with real-time responses"""
    logger.info("GET /rag/streamchat - streamchat called")
    user_id = claims["sub"]
    user: User = user_svc.get_user_by_id(user_id)
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

    if not _check_bot_access_permission(user, bot_id):
        logger.warning(f"streamchat forbidden: user {user_id} has no access to bot {bot_id}")
        raise ApiError(f"You don't have permission to access bot {bot_id}", status_code=403)

    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError:
        logger.warning("streamchat rejected: invalid JSON in data parameter")
        raise ApiError("Invalid JSON in data parameter", status_code=400)

    logger.debug(f"streamchat question length={len(question)}")
    session = message_service.get_session(bot_id, user_id)
    generate: Callable = rag_svc.ask_with_stream(
        bot_id, user_id, parsed_data, question, session_id=session.id if session else -1
    )
    response_iterator = generate(rag_svc)

    logger.info(f"streamchat streaming started for user_id={user_id} bot_id={bot_id}")
    return StreamingResponse(
        stream_with_db_session(response_iterator),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/transmit_to_alfred/{bot_id:int}")
@with_db_session
def transmit_to_alfred(bot_id: int, claims: dict = Depends(admin_or_user)):
    """Transmit chapters to vector database"""
    logger.info(f"POST /rag/transmit_to_alfred/{bot_id} - transmit_to_alfred called")
    user_id = claims["sub"]
    logger.info(f"User {user_id} transmitting chapters for bot {bot_id} to vector DB")

    started_at = time.perf_counter()
    knowledge_svc.recordChaptersToVectorDB(bot_id)
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    logger.info(f"transmit_to_alfred succeeded for bot_id={bot_id} elapsed_ms={elapsed_ms:.1f}")
    return {"message": "Chapters transmitted to Alfred successfully"}


@router.get("/{bot_id:int}")
@with_db_session
def get_session_history(bot_id: int, claims: dict = Depends(any_role)):
    """Get session history for a bot"""
    logger.info(f"GET /rag/{bot_id} - get_session_history called")
    user_id = claims["sub"]
    session = message_service.get_session(bot_id, user_id)
    if session is None:
        logger.info(f"get_session_history({bot_id}) no session")
        return Response(status_code=204)
    messages = message_service.load_session_history(session_id=session.id)
    if not messages:
        logger.info(f"get_session_history({bot_id}) no messages")
        return Response(status_code=204)

    logger.info(f"get_session_history({bot_id}) succeeded count={len(messages)}")
    return [msg.to_dict() for msg in messages]


@router.delete("")
@with_db_session
def delete_selected_bot_session_history(claims: dict = Depends(any_role)):
    """Delete session history for the selected bot"""
    logger.info("DELETE /rag - delete_selected_bot_session_history called")
    user_id = claims["sub"]
    user: User = user_svc.get_user_by_id(user_id)
    if not user:
        logger.warning(f"delete_selected_bot_session_history rejected: user {user_id} not found")
        raise ApiError("User not found", status_code=401)

    bot_id = user.selected_bot_id
    if not bot_id:
        logger.warning(f"delete_selected_bot_session_history rejected: user {user_id} has no selected bot")
        raise ApiError("Bot_id is required", status_code=400)

    return _delete_session_history(int(bot_id), user_id)


@router.delete("/{bot_id:int}")
@with_db_session
def delete_session_history(bot_id: int, claims: dict = Depends(any_role)):
    """Delete session history for a bot"""
    logger.info(f"DELETE /rag/{bot_id} - delete_session_history called")
    return _delete_session_history(bot_id, claims["sub"])


def _delete_session_history(bot_id: int, user_id):
    logger.info(f"User {user_id} deleting session history for bot {bot_id}")
    session = message_service.get_session(bot_id, user_id)
    if session is None:
        logger.info(f"_delete_session_history({bot_id}) no session")
        return {"deleted_message_count": 0}

    deleted_message_count = message_service.delete_session_history(session.id)
    logger.info(f"_delete_session_history({bot_id}) succeeded deleted_message_count={deleted_message_count}")
    return {"deleted_message_count": deleted_message_count}
