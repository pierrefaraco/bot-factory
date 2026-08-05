"""Avatar Management REST API Controller"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from marshmallow import Schema, fields, ValidationError

from ai_server.config.constant import USER_ROLE, ADMIN_ROLE, GUEST_ROLE
from ai_server.dao.database import User
from ai_server.decorators.role_required import role_required
from ai_server.dto.avatar_dto import AvatarDto
from ai_server.services.avatar_svc import AvatarService
from ai_server.log.app_logger import AppLogger

CONTROLLER_NAME = "avatar"
CONTROLLER_PATH = "/avatar"

bp = Blueprint(CONTROLLER_NAME, __name__)


class AvatarRandomSchema(Schema):
    """Schema for avatar creation validation"""

    bot_id = fields.Integer(required=True)


class AvatarSchema(Schema):
    """Schema for avatar update validation"""

    id = fields.Integer(required=False)
    bot_id = fields.Integer(required=True)
    hat = fields.Integer(required=False)
    hat_color = fields.Integer(required=False)
    body = fields.Integer(required=False)
    body_color = fields.Integer(required=False)
    eyes = fields.Integer(required=False)
    eyes_color = fields.Integer(required=False)
    mouth = fields.Integer(required=False)
    mouth_color = fields.Integer(required=False)


# Services initialization
avatar_service = AvatarService()
logger = AppLogger()
avatar_schema = AvatarSchema()
avatar_random_schema = AvatarRandomSchema()


@bp.route(f"{CONTROLLER_PATH}/random", methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE])
def create_random_avatar():
    """Create or update an avatar"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()

        validated_data = avatar_random_schema.load(data)
        avatar_dto: AvatarDto = avatar_service.create_random_avatar(
            validated_data["bot_id"]
        )
        status_code = HTTPStatus.CREATED
        if not avatar_dto:
            return jsonify(
                {"error": "Failed to process random avatar"}
            ), HTTPStatus.INTERNAL_SERVER_ERROR

        return jsonify(avatar_dto.to_dict()), status_code

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Avatar random create error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(CONTROLLER_PATH, methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE])
def patch_avatar():
    """Create or update an avatar"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST
        data = request.get_json()
        avatar_service.patch_avatar(data)
        return "", HTTPStatus.NO_CONTENT

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Avatar create/update error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(CONTROLLER_PATH, methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
def create_or_update_avatar():
    """Create or update an avatar"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = avatar_schema.load(data)
        if request.method == "POST":
            avatar_dto: AvatarDto = avatar_service.create(validated_data)
            return jsonify(avatar_dto.to_dict()), HTTPStatus.CREATED

        elif request.method == "PUT":
            avatar_dto: AvatarDto = avatar_service.update_and_return_datat(
                validated_data
            )
            return jsonify(avatar_dto.to_dict()), HTTPStatus.OK

        return jsonify(
            {"error": "Failed to process avatar"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Avatar create/update error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
def get_avatar_by_bot_id(bot_id: int):
    """Get avatar by bot ID"""
    try:
        avatar_dto: AvatarDto = avatar_service.get_avatar_by_bot_id(bot_id)

        if not avatar_dto:
            return jsonify({"error": "Avatar not found"}), HTTPStatus.NOT_FOUND

        return jsonify(avatar_dto.to_dict()), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Get avatar error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
def delete_avatar(bot_id):
    """Delete avatar by bot ID"""
    try:
        success = avatar_service.delete_avatar_by_bot_id(bot_id)

        if not success:
            return jsonify({"error": "Avatar not found"}), HTTPStatus.NOT_FOUND

        return "", HTTPStatus.NO_CONTENT

    except Exception as e:
        logger.error(f"Delete avatar error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
