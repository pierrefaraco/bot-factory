"""RAG (Retrieval-Augmented Generation) REST API Controller"""

from flask import Blueprint, jsonify, request, Response, stream_with_context
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from pydantic import BaseModel, Field, ValidationError

from ai_server.config.openapi import api, pydantic_error_messages
from typing import Callable
import os
import json

from ai_server.services.message_svc import MessageService
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.decorators.role_required import role_required
from ai_server.services.rag_svc import RagService, message_service
from ai_server.api_controllers.rest_bot_parameters import bot_parameters_svc
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


class StreamChatQuery(BaseModel):
    """Query parameters for the SSE stream chat endpoint"""

    question: str = Field(min_length=1)
    bot_id: int
    data: str = Field(default="{}", description="JSON-encoded payload")


class FirstMessageQuery(BaseModel):
    """Query parameters for the welcome-message trigger endpoint"""

    stream: str = "TRUE"
    data: str = Field(default="{}", description="JSON-encoded payload")


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
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = ChatRequest.model_validate(data).model_dump()

        user_id = get_jwt_identity()
        user: User = user_svc.get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED
        selected_bot_id = user.selected_bot_id
        if not selected_bot_id:
            return jsonify(
                {"error": f"You have to select a bot on the app"}
            ), HTTPStatus.CONFLICT
        # Check bot access permission
        if not _check_bot_access_permission(user, selected_bot_id):
            return jsonify(
                {"error": f"You don't have permission to access bot {selected_bot_id}"}
            ), HTTPStatus.FORBIDDEN

        response = rag_svc.ask(selected_bot_id, user_id, validated_data["question"])
        return jsonify({"response": response}), HTTPStatus.OK

    except ValidationError as e:
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Chat error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/trigfirstmessage", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(query=FirstMessageQuery, tags=["rag"], security={"BearerAuth": []})
def trigfirstmessage():
    """Trigger first welcome message for a bot"""
    try:
        user_id = get_jwt_identity()
        user: User = user_svc.get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        bot_id = user.selected_bot_id
        if not bot_id:
            return jsonify({"error": "Bot_id is required"}), HTTPStatus.BAD_REQUEST

        try:
            bot_id = int(bot_id)
        except ValueError:
            return jsonify({"error": "Invalid bot_id format"}), HTTPStatus.BAD_REQUEST

        # Check bot access permission
        if not _check_bot_access_permission(user, bot_id):
            return jsonify(
                {"error": f"You don't have permission to access bot {bot_id}"}
            ), HTTPStatus.FORBIDDEN

        question = bot_parameters_svc.get_welcome_message(user.name, bot_id)
        stream_response = request.args.get("stream", "TRUE").upper() == "TRUE"
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

            return Response(
                stream_with_context(response_iterator),
                mimetype="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream",
                    "Access-Control-Allow-Origin": "*",
                },
            )
        else:
            delete_session_history(bot_id)
            response = rag_svc.ask(bot_id, user_id, question, hide=True)
            logger.debug(f"RAG response generated for bot {bot_id}, user {user_id}")
            return jsonify({"response": response}), HTTPStatus.OK

    except json.JSONDecodeError:
        return jsonify(
            {"error": "Invalid JSON in data parameter"}
        ), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"First message error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/streamchat", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(query=StreamChatQuery, tags=["rag"], security={"BearerAuth": []})
def streamchat():
    """Stream chat endpoint with real-time responses"""
    try:
        user_id = get_jwt_identity()
        user: User = user_svc.get_user_by_id(user_id)

        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        question = request.args.get("question")
        bot_id = request.args.get("bot_id")

        if not question or not question.strip():
            return jsonify(
                {"error": "Question parameter is required"}
            ), HTTPStatus.BAD_REQUEST
        if not bot_id:
            return jsonify({"error": "Bot_id is required"}), HTTPStatus.BAD_REQUEST

        try:
            bot_id = int(bot_id)
        except ValueError:
            return jsonify({"error": "Invalid bot_id format"}), HTTPStatus.BAD_REQUEST

        # Check bot access permission
        if not _check_bot_access_permission(user, bot_id):
            return jsonify(
                {"error": f"You don't have permission to access bot {bot_id}"}
            ), HTTPStatus.FORBIDDEN

        data = json.loads(request.args.get("data", "{}"))
        session = message_service.get_session(bot_id, user_id)
        generate: Callable = rag_svc.ask_with_stream(
            bot_id, user_id, data, question, session_id=session.id if session else -1
        )
        response_iterator = generate(rag_svc)

        return Response(
            stream_with_context(response_iterator),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
            },
        )

    except json.JSONDecodeError:
        return jsonify(
            {"error": "Invalid JSON in data parameter"}
        ), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Stream chat error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/transmit_to_alfred/<int:bot_id>", methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["rag"], security={"BearerAuth": []})
def transmit_to_alfred(bot_id):
    """Transmit chapters to vector database"""
    try:
        user_id = get_jwt_identity()
        logger.info(
            f"User {user_id} transmitting chapters for bot {bot_id} to vector DB"
        )

        knowledge_svc.recordChaptersToVectorDB(bot_id)
        return jsonify(
            {"message": "Chapters transmitted to Alfred successfully"}
        ), HTTPStatus.OK

    except Exception as exc:
        logger.error(f"Transmit to Alfred error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["rag"], security={"BearerAuth": []})
def get_session_history(bot_id: int):
    """Get session history for a bot"""
    try:
        user_id = get_jwt_identity()
        session = message_service.get_session(bot_id, user_id)
        if session is None:
            return jsonify([]), HTTPStatus.NO_CONTENT
        messages = message_service.load_session_history(session_id=session.id)
        if not messages:
            return jsonify([]), HTTPStatus.NO_CONTENT

        return jsonify([msg.to_dict() for msg in messages]), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Error loading session history: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["rag"], security={"BearerAuth": []})
def delete_selected_bot_session_history():
    """Delete session history for the selected bot"""
    try:
        user_id = get_jwt_identity()
        user: User = user_svc.get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        bot_id = user.selected_bot_id
        if not bot_id:
            return jsonify({"error": "Bot_id is required"}), HTTPStatus.BAD_REQUEST

        bot_id = int(bot_id)
        return _delete_session_history(bot_id, user_id)

    except Exception as e:
        logger.error(f"Error deleting session history: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["rag"], security={"BearerAuth": []})
def delete_session_history(bot_id: int):
    """Delete session history for a bot"""
    try:
        user_id = get_jwt_identity()
        return _delete_session_history(bot_id, user_id)
    except Exception as e:
        logger.error(f"Error deleting session history: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


def _delete_session_history(bot_id: int, user_id: int):
    logger.info(f"User {user_id} deleting session history for bot {bot_id}")

    session = message_service.get_session(bot_id, user_id)
    if session is None:
        return jsonify({"deleted_message_count": 0}), HTTPStatus.OK

    deleted_message_count = message_service.delete_session_history(session.id)
    return jsonify({"deleted_message_count": deleted_message_count}), HTTPStatus.OK
