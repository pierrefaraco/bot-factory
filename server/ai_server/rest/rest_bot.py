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
    logger.info(f"POST {CONTROLLER_PATH} - create_bot called")
    try:
        user_account_id = get_jwt_identity()
        if not user_account_id:
            logger.warning("create_bot rejected: missing user id in JWT")
            return jsonify({"error": "User ID is required"}), HTTPStatus.BAD_REQUEST

        # bot_dto: BotDto = bot_svc.create({'user_account_id': user_account_id})
        bot_dto: BotDto = bot_svc.create_random_bot(user_account_id)
        if bot_dto:
            logger.info(
                f"create_bot succeeded for user_account_id={user_account_id} "
                f"bot_id={bot_dto.id} - status={HTTPStatus.CREATED}"
            )
            return jsonify(bot_dto.to_dict()), HTTPStatus.CREATED

        logger.warning(f"create_bot failed for user_account_id={user_account_id}")
        return jsonify(
            {"error": "Failed to create bot"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR

    except ValidationError as e:
        logger.warning(f"create_bot validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.exception(f"Unexpected error in create_bot: {e}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


class BotViewQuery(BaseModel):
    """Level of detail of the returned bot"""

    view: Optional[str] = "minimal"


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(query=BotViewQuery, tags=["bot"], security={"BearerAuth": []})
def get_bot(bot_id):
    """Get a bot by its ID."""
    logger.info(f"GET {CONTROLLER_PATH}/{bot_id} - get_bot called")
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            logger.warning(f"get_bot({bot_id}) rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED
        view = request.args.get("view", "minimal")
        logger.debug(f"get_bot({bot_id}) params: view={view}")
        bot_dto: Optional[BotDto] = bot_svc.get_dto_by_id(bot_id, view)
        if not bot_dto:
            logger.warning(f"get_bot({bot_id}) not found")
            return jsonify({"error": "Bot not found"}), HTTPStatus.NOT_FOUND

        # Check permissions based on user role
        if user.roles == ADMIN_ROLE:
            # Admin can access any bot
            logger.info(f"get_bot({bot_id}) succeeded - status={HTTPStatus.OK}")
            return jsonify(bot_dto.to_dict()), HTTPStatus.OK
        elif user.roles in (USER_ROLE,GUEST_ROLE):
            # User and guest can access their own bots
            if int(bot_dto.user_account_id) == int(user_id) or bot_svc.is_bot_assigned_to_user(bot_id, user_id) :
                logger.info(f"get_bot({bot_id}) succeeded - status={HTTPStatus.OK}")
                return jsonify(bot_dto.to_dict()), HTTPStatus.OK
        logger.warning(
            f"get_bot({bot_id}) forbidden for user_id={user_id} "
            f"(bot owner={bot_dto.user_account_id})"
        )
        return jsonify(
            {
                "error": f"You don't have rights to get bot {bot_id}. bot_dto.user_account_id{bot_dto.user_account_id} user_id{user_id}"
            }
        ), HTTPStatus.FORBIDDEN
    except Exception as e:
        logger.exception(f"Error getting bot {bot_id}: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/me", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def get_user_bots():
    """Récupère tous les bots d'un utilisateur"""
    logger.info(f"GET {CONTROLLER_PATH}/me - get_user_bots called")
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            logger.warning(f"get_user_bots rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED
        # get_owned_and_assigned_bots already merges both for any role: a
        # Guest owns nothing (get_bots_by_user is always empty for them), so
        # it degrades to assigned-only automatically -- adding
        # get_assigned_bots() on top of it here duplicated every assigned
        # bot for every caller, Guest included (2 "Select bot N" buttons per
        # assigned bot in the UI, strict-mode failures in bot-workspace.spec.ts).
        bots_dto: List[BotDto] = bot_svc.get_owned_and_assigned_bots(user_id)
        logger.info(
            f"get_user_bots succeeded for user_id={user_id} count={len(bots_dto)} "
            f"- status={HTTPStatus.OK}"
        )
        return jsonify([bot_dto.to_dict() for bot_dto in bots_dto]), HTTPStatus.OK
    except Exception as e:
        logger.exception(f"Error getting bots for current user: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def get_all_bots():
    """Récupère tous les bots"""
    logger.info(f"GET {CONTROLLER_PATH} - get_all_bots called")
    try:
        bots_dto: List[BotDto] = bot_svc.get_all()
        logger.info(f"get_all_bots succeeded count={len(bots_dto)} - status={HTTPStatus.OK}")
        return jsonify([bot_dto.to_dict() for bot_dto in bots_dto]), HTTPStatus.OK
    except Exception as e:
        logger.exception(f"Error getting all bots: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/owned", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def get_all_owned_bots():
    """Récupère tous les bots"""
    user_id = get_jwt_identity()
    logger.info(f"GET {CONTROLLER_PATH}/owned - get_all_owned_bots called for user_id={user_id}")
    try:
        bots_dto: List[BotDto] = bot_svc.get_bots_by_user(user_id)
        logger.info(
            f"get_all_owned_bots succeeded for user_id={user_id} count={len(bots_dto)} "
            f"- status={HTTPStatus.OK}"
        )
        return jsonify([bot_dto.to_dict() for bot_dto in bots_dto]), HTTPStatus.OK
    except Exception as e:
        logger.exception(f"Error getting owned bots for user {user_id}: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=BotUpdateRequest, tags=["bot"], security={"BearerAuth": []})
def update_bot_admin(bot_id):
    """Met à jour un bot existant"""
    logger.info(f"PUT {CONTROLLER_PATH}/{bot_id} - update_bot_admin called")
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()

        if not user:
            logger.warning(f"update_bot_admin({bot_id}) rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        if not _can_modify_bot(user, bot_id):
            logger.warning(f"update_bot_admin({bot_id}) forbidden for user_id={user_id}")
            return jsonify(
                {"error": f"You don't have rights to update bot {bot_id}."}
            ), HTTPStatus.FORBIDDEN

        return __update_bot(bot_id)
    except Exception as e:
        logger.exception(f"Error updating bot {bot_id}: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


def __update_bot(bot_id):
    """Met à jour un bot existant"""
    try:
        data = request.get_json()
        logger.debug(f"update_bot({bot_id}) payload keys: {list(data.keys()) if data else []}")
        validated_data = (
            BotUpdateRequest.model_validate(data).model_dump(exclude_unset=True)
            if data
            else {}
        )
        bot_dto: BotDto = bot_svc.update(bot_id, validated_data)
        if not bot_dto:
            logger.warning(f"update_bot({bot_id}) not found")
            return jsonify({"error": "Bot not found"}), HTTPStatus.NOT_FOUND

        logger.info(f"update_bot({bot_id}) succeeded - status={HTTPStatus.OK}")
        return jsonify(bot_dto.to_dict()), HTTPStatus.OK

    except ValidationError as e:
        logger.warning(f"update_bot({bot_id}) validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.exception(f"Error updating bot {bot_id}: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:bot_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def delete_bot(bot_id):
    """Supprime un bot"""
    logger.info(f"DELETE {CONTROLLER_PATH}/{bot_id} - delete_bot called")
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()

        if not user:
            logger.warning(f"delete_bot({bot_id}) rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        if not _can_modify_bot(user, bot_id):
            logger.warning(f"delete_bot({bot_id}) forbidden for user_id={user_id}")
            return jsonify(
                {"error": f"You don't have rights to delete bot {bot_id}"}
            ), HTTPStatus.FORBIDDEN

        return __delete_bot(bot_id)
    except Exception as e:
        logger.exception(f"Error deleting bot {bot_id}: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


def __delete_bot(bot_id):
    """Supprime un bot"""
    try:
        if not bot_svc.delete(bot_id):
            logger.warning(f"delete_bot({bot_id}) not found")
            return jsonify({"error": "Bot not found"}), HTTPStatus.NOT_FOUND

        logger.info(f"delete_bot({bot_id}) succeeded - status={HTTPStatus.NO_CONTENT}")
        return "", HTTPStatus.NO_CONTENT
    except Exception as e:
        logger.exception(f"Error deleting bot {bot_id}: {str(e)}")
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
    logger.info(f"GET {CONTROLLER_PATH}/parameters-description - get_bot_parameters_description called")
    try:
        result = bot_svc.get_bot_parameters_description()
        logger.info(f"get_bot_parameters_description succeeded - status={HTTPStatus.OK}")
        return jsonify(result), 200
    except Exception as e:
        logger.exception(f"Error getting bot parameters description: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/selectbot/<int:bot_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["bot"], security={"BearerAuth": []})
def select_bot(bot_id: int):
    """
    Select a bot by its ID and user ID.
    """
    logger.info(f"PATCH {CONTROLLER_PATH}/selectbot/{bot_id} - select_bot called")
    try:
        user_id = get_jwt_identity()
        user: User = User.query.filter_by(id=user_id).first()
        if not user:
            logger.warning(f"select_bot({bot_id}) rejected: user {user_id} not found")
            return jsonify({"error": "User not found"}), HTTPStatus.UNAUTHORIZED

        user.selected_bot_id = bot_id
        db.session.commit()
        logger.info(
            f"select_bot({bot_id}) succeeded for user_id={user_id} "
            f"- status={HTTPStatus.NO_CONTENT}"
        )
        return "", HTTPStatus.NO_CONTENT
    except Exception as e:
        logger.exception(f"Error selecting bot {bot_id}: {str(e)}")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.before_request
def handle_json():
    if request.method in ["POST", "PUT"] and not request.is_json:
        return jsonify(
            {"error": "Content-Type must be application/json"}
        ), HTTPStatus.BAD_REQUEST
