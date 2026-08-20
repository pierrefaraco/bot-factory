"""RAG (Retrieval-Augmented Generation) REST API Controller"""

from flask import Blueprint, jsonify, request, Response, stream_with_context
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from pydantic import BaseModel, Field, ValidationError

from ai_server.config.openapi import api, pydantic_error_messages
from typing import Callable
import os
import json
import time

from ai_server.services.message_svc import MessageService
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.decorators.role_required import role_required
from ai_server.services.rag_svc import RagService, message_service
from ai_server.rest.rest_bot_parameters import bot_parameters_svc
from ai_server.services.knowledge_svc import KnowledgeSvc
from ai_server.services.bot_assignment_svc import BotAssignmentService
from ai_server.dao.database import User
from ai_server.config.constant import ADMIN_ROLE, USER_ROLE, GUEST_ROLE
from ai_server.services.user_admin_svc import UserAdminService

CONTROLLER_NAME = "rag"
CONTROLLER_PATH = "/" + CONTROLLER_NAME

UPLOAD_FOLDER = "/tmp/"
bp = Blueprint(CONTROLLER_NAME, __name__)


class ChatRequest(BaseModel):
    """Schema for chat validation"""

    question: str = Field(min_length=1)


class StreamChatRequest(BaseModel):
    """Schema for stream chat validation"""

    question: str = Field(min_length=1)
    bot_id: int
    data: dict = Field(default_factory=dict)


# Services initialization
logger = BotFactoryLogger()
rag_svc = RagService()
knowledge_svc = KnowledgeSvc(rag_svc)
bot_assignment_svc = BotAssignmentService()
user_svc = UserAdminService()


def _check_bot_access_permission(user: User, bot_id: int) -> bool:
    """
    Check if user has permission to access a bot.

    Args:
        user: User object
        bot_id: ID of the bot to check

    Returns:
        True if user can access the bot, False otherwise
    """
    from ai_server.services.bot_svc import BotService

    bot_svc = BotService()

    if user.roles == ADMIN_ROLE:
        # Admin can access any bot
        return True
    elif user.roles == USER_ROLE:
        # User can access their own bots
        return bot_svc.is_bot_belong_to_user(bot_id, user.id)
    elif user.roles == GUEST_ROLE:
        # Guest can only access assigned bots
        return bot_assignment_svc.is_bot_assigned_to_user(bot_id, user.id)
    else:
        return False


@bp.route(CONTROLLER_PATH + "/chat", methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(json=ChatRequest, tags=["rag"], security={"BearerAuth": []})
def chat():
    """Basic chat endpoint"""
    logger.info(f"POST {CONTROLLER_PATH}/chat - chat called")
    try:
        if not request.is_json:
            logger.warning("chat rejected: Content-Type is not application/json")
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = ChatRequest.model_validate(data).model_dump()
        logger.debug(f"chat question length={len(validated_data['question'])}")

        user_id = get_jwt_identity()
        user: User = user_svc.get_user_by_id(user_id)
        if not user:
            logger.warning(f"chat rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED
        selected_bot_id = user.selected_bot_id
        if not selected_bot_id:
            logger.warning(f"chat rejected: user {user_id} has no selected bot")
            return jsonify(
                {"error": f"You have to select a bot on the app"}
            ), HTTPStatus.CONFLICT
        # Check bot access permission
        if not _check_bot_access_permission(user, selected_bot_id):
            logger.warning(
                f"chat forbidden: user {user_id} has no access to bot {selected_bot_id}"
            )
            return jsonify(
                {"error": f"You don't have permission to access bot {selected_bot_id}"}
            ), HTTPStatus.FORBIDDEN

        started_at = time.perf_counter()
        response = rag_svc.ask(selected_bot_id, user_id, validated_data["question"])
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            f"chat succeeded for user_id={user_id} bot_id={selected_bot_id} "
            f"elapsed_ms={elapsed_ms:.1f} - status={HTTPStatus.OK}"
        )
        return jsonify({"response": response}), HTTPStatus.OK

    except ValidationError as e:
        logger.warning(f"chat validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"Chat error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/trigfirstmessage", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
# No @api.validate here (unlike other routes in this file): its Flask
# plugin calls response.get_data() unconditionally on any flask.Response
# returned by the view -- see spectree/plugins/flask_plugin.py,
# validate_response() -- which forces this endpoint's streamed SSE
# Response to fully drain into memory and rebuilds a brand-new buffered
# Response from the result, before Werkzeug ever writes a byte to the
# socket. Confirmed empirically: the whole answer arrived in one burst at
# curl even with zero proxies in front of Flask, direct_passthrough=True
# on the Response, and a verified-streaming LangChain chain underneath --
# only removing this decorator fixed it. Auth is unaffected: role_required
# already wraps @jwt_required() itself (ai_server/decorators/role_required.py),
# and query args are validated manually below regardless (the function
# never reads request.context, so @api.validate's query model was never
# actually consumed).
def trigfirstmessage():
    """Trigger first welcome message for a bot"""
    logger.info(f"GET {CONTROLLER_PATH}/trigfirstmessage - trigfirstmessage called")
    try:
        user_id = get_jwt_identity()
        user: User = user_svc.get_user_by_id(user_id)
        if not user:
            logger.warning(f"trigfirstmessage rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        bot_id = user.selected_bot_id
        if not bot_id:
            logger.warning(f"trigfirstmessage rejected: user {user_id} has no selected bot")
            return jsonify({"error": "Bot_id is required"}), HTTPStatus.BAD_REQUEST

        try:
            bot_id = int(bot_id)
        except ValueError:
            logger.warning(f"trigfirstmessage rejected: invalid bot_id format {bot_id!r}")
            return jsonify({"error": "Invalid bot_id format"}), HTTPStatus.BAD_REQUEST

        # Check bot access permission
        if not _check_bot_access_permission(user, bot_id):
            logger.warning(
                f"trigfirstmessage forbidden: user {user_id} has no access to bot {bot_id}"
            )
            return jsonify(
                {"error": f"You don't have permission to access bot {bot_id}"}
            ), HTTPStatus.FORBIDDEN

        question = bot_parameters_svc.get_welcome_message(user.name, bot_id)
        stream_response = request.args.get("stream", "TRUE").upper() == "TRUE"
        logger.debug(f"trigfirstmessage params: bot_id={bot_id} stream={stream_response}")
        if stream_response:
            data = json.loads(request.args.get("data", "{}"))
            session = message_service.get_session(bot_id, user_id)
            generate: Callable = rag_svc.ask_with_stream(
                bot_id,
                user_id,
                data,
                question,
                hide=True,
                session_id=session.id if session else -1,
            )
            response_iterator = generate(rag_svc)

            logger.info(
                f"trigfirstmessage streaming started for user_id={user_id} bot_id={bot_id}"
            )
            return Response(
                stream_with_context(response_iterator),
                mimetype="text/event-stream",
                # NOT direct_passthrough=True: that skips Werkzeug's
                # automatic str->bytes encoding of yielded chunks
                # (Response.iter_encoded), but rag_svc.py's generator
                # yields plain `str` (f-strings), not `bytes` -- Werkzeug's
                # dev server asserts `isinstance(data, bytes)` on write and
                # crashes mid-response with direct_passthrough on. Not
                # needed anyway: the actual bug was @api.validate silently
                # calling response.get_data() (removed above, see that
                # comment) -- nothing else in this codebase touches the
                # response body, so the default (False) is fine here.
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream",
                    "Access-Control-Allow-Origin": "*",
                    # Standard signal nginx honors to disable proxy_buffering
                    # for this response specifically -- defense in depth
                    # alongside the `proxy_buffering off` now set on the
                    # /api/ location itself (client/nginx.conf.template);
                    # without either, nginx buffers the whole SSE stream and
                    # delivers it to the browser in one shot at the end,
                    # even though this generator yields per LLM chunk.
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            delete_session_history(bot_id)
            started_at = time.perf_counter()
            response = rag_svc.ask(bot_id, user_id, question, hide=True)
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.info(
                f"trigfirstmessage succeeded for user_id={user_id} bot_id={bot_id} "
                f"elapsed_ms={elapsed_ms:.1f} - status={HTTPStatus.OK}"
            )
            return jsonify({"response": response}), HTTPStatus.OK

    except json.JSONDecodeError:
        logger.warning("trigfirstmessage rejected: invalid JSON in data parameter")
        return jsonify(
            {"error": "Invalid JSON in data parameter"}
        ), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"First message error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/streamchat", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
# No @api.validate here -- cf. the identical comment on trigfirstmessage()
# above for why (spectree's Flask plugin unconditionally drains streamed
# Response bodies via get_data() before Werkzeug can stream them).
def streamchat():
    """Stream chat endpoint with real-time responses"""
    logger.info(f"GET {CONTROLLER_PATH}/streamchat - streamchat called")
    try:
        user_id = get_jwt_identity()
        user: User = user_svc.get_user_by_id(user_id)

        if not user:
            logger.warning(f"streamchat rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        question = request.args.get("question")
        bot_id = request.args.get("bot_id")

        if not question or not question.strip():
            logger.warning(f"streamchat rejected: missing question for user {user_id}")
            return jsonify(
                {"error": "Question parameter is required"}
            ), HTTPStatus.BAD_REQUEST
        if not bot_id:
            logger.warning(f"streamchat rejected: missing bot_id for user {user_id}")
            return jsonify({"error": "Bot_id is required"}), HTTPStatus.BAD_REQUEST

        try:
            bot_id = int(bot_id)
        except ValueError:
            logger.warning(f"streamchat rejected: invalid bot_id format {bot_id!r}")
            return jsonify({"error": "Invalid bot_id format"}), HTTPStatus.BAD_REQUEST

        # Check bot access permission
        if not _check_bot_access_permission(user, bot_id):
            logger.warning(
                f"streamchat forbidden: user {user_id} has no access to bot {bot_id}"
            )
            return jsonify(
                {"error": f"You don't have permission to access bot {bot_id}"}
            ), HTTPStatus.FORBIDDEN

        data = json.loads(request.args.get("data", "{}"))
        logger.debug(f"streamchat question length={len(question)}")
        session = message_service.get_session(bot_id, user_id)
        generate: Callable = rag_svc.ask_with_stream(
            bot_id, user_id, data, question, session_id=session.id if session else -1
        )
        response_iterator = generate(rag_svc)

        logger.info(f"streamchat streaming started for user_id={user_id} bot_id={bot_id}")
        return Response(
            stream_with_context(response_iterator),
            mimetype="text/event-stream",
            # No direct_passthrough=True here -- cf. the comment in
            # trigfirstmessage() above (it breaks Werkzeug's str->bytes
            # encoding for this generator's plain-str yields).
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                # Cf. same header in trigfirstmessage() above.
                "X-Accel-Buffering": "no",
            },
        )

    except json.JSONDecodeError:
        logger.warning("streamchat rejected: invalid JSON in data parameter")
        return jsonify(
            {"error": "Invalid JSON in data parameter"}
        ), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"Stream chat error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/transmit_to_alfred/<int:bot_id>", methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["rag"], security={"BearerAuth": []})
def transmit_to_alfred(bot_id):
    """Transmit chapters to vector database"""
    logger.info(f"POST {CONTROLLER_PATH}/transmit_to_alfred/{bot_id} - transmit_to_alfred called")
    try:
        user_id = get_jwt_identity()
        logger.info(
            f"User {user_id} transmitting chapters for bot {bot_id} to vector DB"
        )

        started_at = time.perf_counter()
        knowledge_svc.recordChaptersToVectorDB(bot_id)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            f"transmit_to_alfred succeeded for bot_id={bot_id} "
            f"elapsed_ms={elapsed_ms:.1f} - status={HTTPStatus.OK}"
        )
        return jsonify(
            {"message": "Chapters transmitted to Alfred successfully"}
        ), HTTPStatus.OK

    except Exception as exc:
        logger.exception(f"Transmit to Alfred error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["rag"], security={"BearerAuth": []})
def get_session_history(bot_id: int):
    """Get session history for a bot"""
    logger.info(f"GET {CONTROLLER_PATH}/{bot_id} - get_session_history called")
    try:
        user_id = get_jwt_identity()
        session = message_service.get_session(bot_id, user_id)
        if session is None:
            logger.info(f"get_session_history({bot_id}) no session - status={HTTPStatus.NO_CONTENT}")
            return jsonify([]), HTTPStatus.NO_CONTENT
        messages = message_service.load_session_history(session_id=session.id)
        if not messages:
            logger.info(f"get_session_history({bot_id}) no messages - status={HTTPStatus.NO_CONTENT}")
            return jsonify([]), HTTPStatus.NO_CONTENT

        logger.info(
            f"get_session_history({bot_id}) succeeded count={len(messages)} "
            f"- status={HTTPStatus.OK}"
        )
        return jsonify([msg.to_dict() for msg in messages]), HTTPStatus.OK

    except Exception as e:
        logger.exception(f"Error loading session history: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["rag"], security={"BearerAuth": []})
def delete_selected_bot_session_history():
    """Delete session history for the selected bot"""
    logger.info(f"DELETE {CONTROLLER_PATH} - delete_selected_bot_session_history called")
    try:
        user_id = get_jwt_identity()
        user: User = user_svc.get_user_by_id(user_id)
        if not user:
            logger.warning(f"delete_selected_bot_session_history rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        bot_id = user.selected_bot_id
        if not bot_id:
            logger.warning(
                f"delete_selected_bot_session_history rejected: user {user_id} has no selected bot"
            )
            return jsonify({"error": "Bot_id is required"}), HTTPStatus.BAD_REQUEST

        bot_id = int(bot_id)
        return _delete_session_history(bot_id, user_id)

    except Exception as e:
        logger.exception(f"Error deleting session history: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["rag"], security={"BearerAuth": []})
def delete_session_history(bot_id: int):
    """Delete session history for a bot"""
    logger.info(f"DELETE {CONTROLLER_PATH}/{bot_id} - delete_session_history called")
    try:
        user_id = get_jwt_identity()
        return _delete_session_history(bot_id, user_id)
    except Exception as e:
        logger.exception(f"Error deleting session history: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


def _delete_session_history(bot_id: int, user_id: int):
    logger.info(f"User {user_id} deleting session history for bot {bot_id}")

    session = message_service.get_session(bot_id, user_id)
    if session is None:
        logger.info(f"_delete_session_history({bot_id}) no session - status={HTTPStatus.OK}")
        return jsonify({"deleted_message_count": 0}), HTTPStatus.OK

    deleted_message_count = message_service.delete_session_history(session.id)
    logger.info(
        f"_delete_session_history({bot_id}) succeeded "
        f"deleted_message_count={deleted_message_count} - status={HTTPStatus.OK}"
    )
    return jsonify({"deleted_message_count": deleted_message_count}), HTTPStatus.OK
