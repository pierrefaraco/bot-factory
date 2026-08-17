from typing import List, Optional
from flask import Blueprint, request, jsonify
from http import HTTPStatus
from flask_jwt_extended import get_jwt_identity
from pydantic import BaseModel, ValidationError, field_validator

from ai_server.config.constant import USER_ROLE, ADMIN_ROLE, GUEST_ROLE
from ai_server.config.openapi import api, pydantic_error_messages
from ai_server.dao.database import User, db
from ai_server.decorators.role_required import role_required
from ai_server.dto.bot_dto import BotDto
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.bot_svc import BotService
from ai_server.services.message_svc import MessageService

CONTROLLER_NAME = "bot"
CONTROLLER_PATH = "/bot"

bp = Blueprint(CONTROLLER_NAME, __name__)


class BotUpdateRequest(BaseModel):
    """Schéma de validation pour les bots"""

    id: Optional[int] = None
    user_account_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("name must not be blank")
        return value


# Services initialization
bot_svc = BotService()
message_svc = MessageService()
logger = BotFactoryLogger()


@bp.route(CONTROLLER_PATH, methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def create_bot():
    """Create a new bot with random parameters for the authenticated user."""
    try:
        user_account_id = get_jwt_identity()
        if not user_account_id:
            return jsonify({"error": "User ID is required"}), HTTPStatus.BAD_REQUEST

        # bot_dto: BotDto = bot_svc.create({'user_account_id': user_account_id})
        bot_dto: BotDto = bot_svc.create_random_bot(user_account_id)
        if bot_dto:
            return jsonify(bot_dto.to_dict()), HTTPStatus.CREATED

        return jsonify(
            {"error": "Failed to create bot"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR

    except ValidationError as e:
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


class BotViewQuery(BaseModel):
    """Level of detail of the returned bot"""

    view: Optional[str] = "minimal"


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(query=BotViewQuery, tags=["bot"], security={"BearerAuth": []})
def get_bot(bot_id):
    """Get a bot by its ID."""
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED
        view = request.args.get("view", "minimal")
        logger.info(f"view {view}")
        bot_dto: Optional[BotDto] = bot_svc.get_dto_by_id(bot_id, view)
        if not bot_dto:
            return jsonify({"error": "Bot not found"}), HTTPStatus.NOT_FOUND

        # Check permissions based on user role
        if user.roles == ADMIN_ROLE:
            # Admin can access any bot
            pass
        elif user.roles == USER_ROLE:
            # User can access their own bots
            if int(bot_dto.user_account_id) != int(user_id):
                return jsonify(
                    {
                        "error": f"You don't have rights to get bot {bot_id}. bot_dto.user_account_id{bot_dto.user_account_id} user_id{user_id}"
                    }
                ), HTTPStatus.FORBIDDEN
        elif user.roles == GUEST_ROLE:
            # Guest can only access assigned bots
            if not bot_svc.is_bot_assigned_to_user(bot_id, user_id):
                return jsonify(
                    {"error": f"Bot {bot_id} is not assigned to you."}
                ), HTTPStatus.FORBIDDEN
        else:
            return jsonify({"error": "Invalid user role"}), HTTPStatus.FORBIDDEN

        return jsonify(bot_dto.to_dict()), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Error getting bot {bot_id}: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/self", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def get_user_bots():
    """Récupère tous les bots d'un utilisateur"""
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        if user.roles == GUEST_ROLE:
            # For GUEST users, get only assigned bots
            bots_dto: List[BotDto] = bot_svc.get_assigned_bots(user_id)
            return jsonify([bot_dto.to_dict() for bot_dto in bots_dto]), HTTPStatus.OK
        else:
            # For USER and ADMIN, get their own bots
            bots_dto: List[BotDto] = bot_svc.get_bots_by_user(user_id)
            return jsonify([bot_dto.to_dict() for bot_dto in bots_dto]), HTTPStatus.OK
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def get_all_bots():
    """Récupère tous les bots"""
    try:
        bots_dto: List[BotDto] = bot_svc.get_all()
        return jsonify([bot_dto.to_dict() for bot_dto in bots_dto]), HTTPStatus.OK
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/owned", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def get_all_owned_bots():
    """Récupère tous les bots"""
    user_id = get_jwt_identity()
    try:
        bots_dto: List[BotDto] = bot_svc.get_bots_by_user(user_id)
        return jsonify([bot_dto.to_dict() for bot_dto in bots_dto]), HTTPStatus.OK
    except Exception as e:
        logger.error(f"Error getting owned bots for user {user_id}: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=BotUpdateRequest, tags=["bot"], security={"BearerAuth": []})
def update_bot_admin(bot_id):
    """Met à jour un bot existant"""
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        if not _can_modify_bot(user, bot_id):
            return jsonify(
                {"error": f"You don't have rights to update bot {bot_id}."}
            ), HTTPStatus.FORBIDDEN

        return __update_bot(bot_id)
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


def __update_bot(bot_id):
    """Met à jour un bot existant"""
    try:
        data = request.get_json()
        validated_data = (
            BotUpdateRequest.model_validate(data).model_dump(exclude_unset=True)
            if data
            else {}
        )
        bot_dto: BotDto = bot_svc.update(bot_id, validated_data)
        if not bot_dto:
            return jsonify({"error": "Bot not found"}), HTTPStatus.NOT_FOUND

        return jsonify(bot_dto.to_dict()), HTTPStatus.OK

    except ValidationError as e:
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def delete_bot(bot_id):
    """Supprime un bot"""
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        if not _can_modify_bot(user, bot_id):
            return jsonify(
                {"error": f"You don't have rights to delete bot {bot_id}"}
            ), HTTPStatus.FORBIDDEN

        return __delete_bot(bot_id)
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


def __delete_bot(bot_id):
    """Supprime un bot"""
    try:
        logger.info("delete bot")
        if not bot_svc.delete(bot_id):
            return jsonify({"error": "Bot not found"}), HTTPStatus.NOT_FOUND

        return "", HTTPStatus.NO_CONTENT
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


def _can_modify_bot(user: User, bot_id: int) -> bool:
    """Vérifie si l'utilisateur peut modifier le bot"""
    if user.roles == ADMIN_ROLE:
        return True

    bot_dto: BotDto = bot_svc.get_dto_by_id(bot_id)
    return bot_dto and bot_dto.user_account_id == user.id


@bp.route(f"{CONTROLLER_PATH}/parameters-description", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def get_bot_parameters_description():
    try:
        return jsonify(bot_svc.get_bot_parameters_description()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/selectbot/<int:bot_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def select_bot(bot_id: int):
    """
    Select a bot by its ID and user ID.
    """
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        user.selected_bot_id = bot_id
        db.session.commit()
        return "", HTTPStatus.NO_CONTENT
    except Exception as e:
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.before_request
def handle_json():
    if request.method in ["POST", "PUT"] and not request.is_json:
        return jsonify(
            {"error": "Content-Type must be application/json"}
        ), HTTPStatus.BAD_REQUEST
