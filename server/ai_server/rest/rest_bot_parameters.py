thd = """Bot Parameters REST API Controller"""
from typing import Optional

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from pydantic import BaseModel, ValidationError

from ai_server.config.openapi import api, pydantic_error_messages
from ai_server.dao.database import User
from ai_server.dto.bot_parameters_dto import BotParametersDto
from ai_server.services.bot_parameters_svc import BotParametersService
from ai_server.config.constant import USER_ROLE, ADMIN_ROLE, GUEST_ROLE
from ai_server.decorators.role_required import role_required
from ai_server.log.bot_factory_logger import BotFactoryLogger

CONTROLLER_NAME = "bot-parameters"
CONTROLLER_PATH = "/bot-parameters"

bp = Blueprint(CONTROLLER_NAME, __name__)


class BotParametersRequest(BaseModel):
    """Schema for bot parameters validation"""

    bot_id: int
    answer_length: Optional[str] = None
    answer_style: Optional[str] = None
    behaviour_when_ignore: Optional[str] = None
    behaviour_with_language: Optional[str] = None
    bot_name: Optional[str] = None
    bot_type: Optional[str] = None
    context_type: Optional[str] = None
    goal: Optional[str] = None
    interlocutor_identity: Optional[str] = None
    interlocutor_type: Optional[str] = None
    localisation: Optional[str] = None
    main_personality_trait_1: Optional[str] = None
    main_personality_trait_2: Optional[str] = None
    main_personality_trait_3: Optional[str] = None
    used_sources: Optional[str] = None
    answer_format: Optional[str] = None
    voice_output: Optional[bool] = None
    persona_description: Optional[str] = None


class BotParametersPatchRequest(BaseModel):
    """Schema for bot parameters patch validation: any subset of the
    BotParametersRequest fields (all optional)"""

    class Config:
        extra = "allow"


# Services initialization
bot_parameters_svc = BotParametersService()
logger = BotFactoryLogger()


@bp.route(CONTROLLER_PATH, methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(
    json=BotParametersRequest, tags=["bot-parameters"], security={"BearerAuth": []}
)
def create_or_update_bot_parameters():
    """Create bot parameters and regenerate the bot's system prompt."""
    logger.info(f"{request.method} {CONTROLLER_PATH} - create_or_update_bot_parameters called")
    try:
        if not request.is_json:
            logger.warning("create_or_update_bot_parameters rejected: Content-Type is not application/json")
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        logger.debug(f"create_or_update_bot_parameters payload keys: {list(data.keys()) if data else []}")
        validated_data = BotParametersRequest.model_validate(data).model_dump(
            exclude_unset=True
        )

        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            logger.warning(f"create_or_update_bot_parameters rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        bot_parameters_dto = bot_parameters_svc.create_bot_parameters(
            user.name, validated_data["bot_id"], validated_data
        )
        if bot_parameters_dto:
            logger.info(
                f"create_or_update_bot_parameters succeeded for bot_id={validated_data['bot_id']} "
                f"user_id={user_id} - status={HTTPStatus.CREATED}"
            )
            return jsonify(bot_parameters_dto.to_dict()), HTTPStatus.CREATED

        logger.warning(
            f"create_or_update_bot_parameters failed for bot_id={validated_data.get('bot_id')} user_id={user_id}"
        )
        return jsonify(
            {"error": "Failed to process bot parameters"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR

    except ValidationError as e:
        logger.warning(f"create_or_update_bot_parameters validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.exception(f"Bot parameters create/update error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(
    json=BotParametersPatchRequest,
    tags=["bot-parameters"],
    security={"BearerAuth": []},
)
def patch_bot_parameters_admin(bot_id):
    """Partially update bot parameters and regenerate the bot's system prompt.

    Empty-string values are ignored, except for the optional clearable fields
    (persona_description, answer_format).
    """
    logger.info(f"PATCH {CONTROLLER_PATH}/{bot_id} - patch_bot_parameters_admin called")
    try:
        if not request.is_json:
            logger.warning(f"patch_bot_parameters_admin({bot_id}) rejected: Content-Type is not application/json")
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        logger.debug(f"patch_bot_parameters_admin({bot_id}) payload keys: {list(data.keys()) if data else []}")
        validated_data = data

        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            logger.warning(f"patch_bot_parameters_admin({bot_id}) rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        # TODO: Add proper permission check for bot ownership
        if user.roles not in [ADMIN_ROLE, USER_ROLE]:
            logger.warning(f"patch_bot_parameters_admin({bot_id}) forbidden for user_id={user_id}")
            return jsonify(
                {"error": f"You don't have rights to patch bot {bot_id}"}
            ), HTTPStatus.FORBIDDEN

        bot_parameters_dto: BotParametersDto = bot_parameters_svc.patch_bot_parameters(
            bot_id, validated_data, user.name
        )

        if not bot_parameters_dto:
            logger.warning(f"patch_bot_parameters_admin({bot_id}) not found")
            return jsonify({"error": "Bot parameters not found"}), HTTPStatus.NOT_FOUND

        logger.info(f"patch_bot_parameters_admin({bot_id}) succeeded - status={HTTPStatus.OK}")
        return jsonify(bot_parameters_dto.to_dict()), HTTPStatus.OK

    except ValidationError as e:
        logger.warning(f"patch_bot_parameters_admin({bot_id}) validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"Bot parameters patch error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["bot-parameters"], security={"BearerAuth": []})
def get_bot_parameters_by_bot_id(bot_id: int):
    """Get bot parameters by bot ID"""
    logger.info(f"GET {CONTROLLER_PATH}/{bot_id} - get_bot_parameters_by_bot_id called")
    try:
        bot_parameters_dto: BotParametersDto = bot_parameters_svc.get_by_bot_id(bot_id)
        if not bot_parameters_dto:
            logger.warning(f"get_bot_parameters_by_bot_id({bot_id}) not found")
            return jsonify({"error": "Bot parameters not found"}), HTTPStatus.NOT_FOUND

        logger.info(f"get_bot_parameters_by_bot_id({bot_id}) succeeded - status={HTTPStatus.OK}")
        return jsonify(bot_parameters_dto.to_dict()), HTTPStatus.OK

    except Exception as e:
        logger.exception(f"Get bot parameters error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["bot-parameters"], security={"BearerAuth": []})
def delete_bot_parameters(bot_id):
    """Delete bot parameters by bot ID"""
    logger.info(f"DELETE {CONTROLLER_PATH}/{bot_id} - delete_bot_parameters called")
    try:
        success = bot_parameters_svc.delete_by_bot_id(bot_id)
        if not success:
            logger.warning(f"delete_bot_parameters({bot_id}) not found")
            return jsonify({"error": "Bot parameters not found"}), HTTPStatus.NOT_FOUND

        logger.info(f"delete_bot_parameters({bot_id}) succeeded - status={HTTPStatus.NO_CONTENT}")
        return "", HTTPStatus.NO_CONTENT

    except Exception as e:
        logger.exception(f"Delete bot parameters error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
