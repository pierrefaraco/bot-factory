thd = """Bot Parameters REST API Controller"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from marshmallow import Schema, fields, ValidationError

from ai_server.dao.database import User
from ai_server.dto.bot_parameters_dto import BotParametersDto
from ai_server.services.bot_parameters_svc import BotParametersService
from ai_server.config.constant import USER_ROLE, ADMIN_ROLE, GUEST_ROLE
from ai_server.decorators.role_required import role_required
from ai_server.log.bot_factory_logger import BotFactoryLogger

CONTROLLER_NAME = "bot-parameters"
CONTROLLER_PATH = "/bot-parameters"

bp = Blueprint(CONTROLLER_NAME, __name__)


class BotParametersSchema(Schema):
    """Schema for bot parameters validation"""

    bot_id = fields.Integer(required=True)
    answer_length = fields.String(required=False)
    answer_style = fields.String(required=False)
    behaviour_when_ignore = fields.String(required=False)
    behaviour_with_language = fields.String(required=False)
    bot_name = fields.String(required=False)
    bot_type = fields.String(required=False)
    context_type = fields.String(required=False)
    goal = fields.String(required=False)
    interlocutor_identity = fields.String(required=False)
    interlocutor_type = fields.String(required=False)
    localisation = fields.String(required=False)
    main_personality_trait_1 = fields.String(required=False)
    main_personality_trait_2 = fields.String(required=False)
    main_personality_trait_3 = fields.String(required=False)
    used_sources = fields.String(required=False)


class BotParametersPatchSchema(Schema):
    """Schema for bot parameters patch validation"""

    parameters = fields.Dict(required=True)


# Services initialization
bot_parameters_svc = BotParametersService()
logger = BotFactoryLogger()
bot_parameters_schema = BotParametersSchema()
bot_parameters_patch_schema = BotParametersPatchSchema()


@bp.route(CONTROLLER_PATH, methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
def create_or_update_bot_parameters():
    """Create or update bot parameters"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = bot_parameters_schema.load(data)

        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        bot_parameters_dto = bot_parameters_svc.create_bot_parameters(
            user.name, validated_data["bot_id"], validated_data
        )
        if bot_parameters_dto:
            return jsonify(bot_parameters_dto.to_dict()), HTTPStatus.CREATED

        return jsonify(
            {"error": "Failed to process bot parameters"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Bot parameters create/update error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE])
def patch_bot_parameters_admin(bot_id):
    """Patch bot parameters"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = data  # bot_parameters_patch_schema.load(data)

        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        # TODO: Add proper permission check for bot ownership
        if user.roles not in [ADMIN_ROLE, USER_ROLE]:
            return jsonify(
                {"error": f"You don't have rights to patch bot {bot_id}"}
            ), HTTPStatus.FORBIDDEN

        bot_parameters_dto: BotParametersDto = bot_parameters_svc.patch_bot_parameters(
            bot_id, validated_data, user.name
        )

        if not bot_parameters_dto:
            return jsonify({"error": "Bot parameters not found"}), HTTPStatus.NOT_FOUND

        return jsonify(bot_parameters_dto.to_dict()), HTTPStatus.OK

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Bot parameters patch error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
def get_bot_parameters_by_bot_id(bot_id: int):
    """Get bot parameters by bot ID"""
    try:
        bot_parameters_dto: BotParametersDto = bot_parameters_svc.get_by_bot_id(bot_id)
        if not bot_parameters_dto:
            return jsonify({"error": "Bot parameters not found"}), HTTPStatus.NOT_FOUND

        return jsonify(bot_parameters_dto.to_dict()), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Get bot parameters error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
def delete_bot_parameters(bot_id):
    """Delete bot parameters by bot ID"""
    try:
        success = bot_parameters_svc.delete_by_bot_id(bot_id)
        if not success:
            return jsonify({"error": "Bot parameters not found"}), HTTPStatus.NOT_FOUND

        return "", HTTPStatus.NO_CONTENT

    except Exception as e:
        logger.error(f"Delete bot parameters error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
