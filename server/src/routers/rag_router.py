"""RAG chat REST API.

The chat routes go through ChatFacade (services/chat_facade.py) for every
step of a conversation turn -- user lookup, bot access check, token
quota, session lookup, RAG call. This module only parses the request and
turns the facade's results into HTTP responses.

Blocking work with no async equivalent (ChromaDB, the retriever step of
the LCEL chain) runs in the threadpool, from rag_svc.py/knowledge_svc.py
or through LangChain's own offloading of sync RunnableLambdas.

Streaming routes (trigfirstmessage?stream=TRUE, streamchat) return an
async generator that saves the assistant's reply on its last step, after
the endpoint has returned: stream_with_async_db_session keeps a DB scope
open around the whole generator (see dependencies/db_session.py).
"""

import time

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from src.dependencies.auth import require_roles
from src.dependencies.content_type import require_json_body
from src.dependencies.db_session import (
    async_db_session_dependency,
    stream_with_async_db_session,
)
from src.dependencies.services import ChatFacadeDep, KnowledgeServiceDep
from src.log.bot_factory_logger import BotFactoryLogger

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


def _sse_response(response_iterator) -> StreamingResponse:
    return StreamingResponse(
        stream_with_async_db_session(response_iterator),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )


@router.post("/chat", dependencies=[Depends(require_json_body(ChatRequest))])
async def chat(
    body: ChatRequest,
    chat_facade: ChatFacadeDep,
    claims: dict = Depends(any_role),
):
    """Basic chat endpoint"""
    logger.info("POST /rag/chat - chat called")
    response = await chat_facade.ask(claims["sub"], body.question)
    return {"response": response}


@router.get("/trigfirstmessage")
async def trigfirstmessage(
    chat_facade: ChatFacadeDep,
    claims: dict = Depends(any_role),
    stream: str = Query(default="TRUE"),
    data: str = Query(default="{}"),
):
    """Trigger first welcome message for a bot"""
    logger.info("GET /rag/trigfirstmessage - trigfirstmessage called")
    user_id = claims["sub"]
    if stream.upper() == "TRUE":
        return _sse_response(await chat_facade.stream_welcome(user_id, data))
    return {"response": await chat_facade.welcome(user_id)}


@router.get("/streamchat")
async def streamchat(
    chat_facade: ChatFacadeDep,
    claims: dict = Depends(any_role),
    question: str = Query(default=None),
    bot_id: str = Query(default=None),
    data: str = Query(default="{}"),
):
    """Stream chat endpoint with real-time responses"""
    logger.info("GET /rag/streamchat - streamchat called")
    return _sse_response(
        await chat_facade.stream(claims["sub"], bot_id, question, data)
    )


@router.post("/reindex/{bot_id:int}")
async def reindex_knowledge(
    bot_id: int,
    knowledge_svc: KnowledgeServiceDep,
    claims: dict = Depends(admin_or_user),
):
    """Rebuild the bot's vector collection from its chapters."""
    logger.info(f"POST /rag/reindex/{bot_id} - reindex_knowledge called")
    user_id = claims["sub"]
    logger.info(f"User {user_id} reindexing the knowledge of bot {bot_id}")

    started_at = time.perf_counter()
    await knowledge_svc.reindex_bot(bot_id)
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    logger.info(f"reindex_knowledge succeeded for bot_id={bot_id} elapsed_ms={elapsed_ms:.1f}")
    return {"message": "Knowledge base reindexed successfully"}


@router.get("/{bot_id:int}")
async def get_session_history(
    bot_id: int,
    chat_facade: ChatFacadeDep,
    claims: dict = Depends(any_role),
):
    """Get session history for a bot"""
    logger.info(f"GET /rag/{bot_id} - get_session_history called")
    messages = await chat_facade.history(bot_id, claims["sub"])
    if not messages:
        logger.info(f"get_session_history({bot_id}) no messages")
        return Response(status_code=204)

    logger.info(f"get_session_history({bot_id}) succeeded count={len(messages)}")
    return [msg.to_dict() for msg in messages]


@router.delete("")
async def delete_selected_bot_session_history(
    chat_facade: ChatFacadeDep,
    claims: dict = Depends(any_role),
):
    """Delete session history for the selected bot"""
    logger.info("DELETE /rag - delete_selected_bot_session_history called")
    deleted = await chat_facade.delete_selected_bot_history(claims["sub"])
    return {"deleted_message_count": deleted}


@router.delete("/{bot_id:int}")
async def delete_session_history(
    bot_id: int,
    chat_facade: ChatFacadeDep,
    claims: dict = Depends(any_role),
):
    """Delete session history for a bot"""
    logger.info(f"DELETE /rag/{bot_id} - delete_session_history called")
    deleted = await chat_facade.delete_history(bot_id, claims["sub"])
    return {"deleted_message_count": deleted}
