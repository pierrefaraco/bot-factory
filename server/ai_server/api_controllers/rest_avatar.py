"""Avatar Management REST API Controller"""

from typing import Optional

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from pydantic import BaseModel, ValidationError

from ai_server.config.constant import USER_ROLE, ADMIN_ROLE, GUEST_ROLE
from ai_server.config.openapi import api, pydantic_error_messages
from ai_server.dao.database import User
from ai_server.decorators.role_required import role_required
from ai_server.dto.avatar_dto import AvatarDto
from ai_server.services.avatar_svc import AvatarService
from ai_server.log.bot_factory_logger import BotFactoryLogger

CONTROLLER_NAME = "avatar"
CONTROLLER_PATH = "/avatar"

bp = Blueprint(CONTROLLER_NAME, __name__)


class AvatarRandomRequest(BaseModel):
    """Schema for avatar creation validation"""

    bot_id: int


class AvatarPatchRequest(BaseModel):
    """Schema for partial avatar update: any subset of the avatar fields"""

    id: Optional[int] = None
    bot_id: Optional[int] = None
    hat: Optional[int] = None
    hat_color: Optional[int] = None
    body: Optional[int] = None
    body_color: Optional[int] = None
    eyes: Optional[int] = None
    eyes_color: Optional[int] = None
    mouth: Optional[int] = None
    mouth_color: Optional[int] = None


class AvatarRequest(BaseModel):
    """Schema for avatar update validation"""

    id: Optional[int] = None
    bot_id: int
    hat: Optional[int] = None
    hat_color: Optional[int] = None
    body: Optional[int] = None
    body_color: Optional[int] = None
    eyes: Optional[int] = None
    eyes_color: Optional[int] = None
    mouth: Optional[int] = None
    mouth_color: Optional[int] = None


# Services initialization
avatar_service = AvatarService()
logger = BotFactoryLogger()


@bp.route(f"{CONTROLLER_PATH}/random", methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=AvatarRandomRequest, tags=["avatar"], security={"BearerAuth": []})
def create_random_avatar():
    """Create or update an avatar"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()

        validated_data = AvatarRandomRequest.model_validate(data).model_dump()
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
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Avatar random create error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(CONTROLLER_PATH, methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=AvatarPatchRequest, tags=["avatar"], security={"BearerAuth": []})
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
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Avatar create/update error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(CONTROLLER_PATH, methods=["POST", "PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=AvatarRequest, tags=["avatar"], security={"BearerAuth": []})
def create_or_update_avatar():
    """Create or update an avatar"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = AvatarRequest.model_validate(data).model_dump(exclude_unset=True)
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
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Avatar create/update error: {e}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["avatar"], security={"BearerAuth": []})
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
@api.validate(tags=["avatar"], security={"BearerAuth": []})
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
