"""User Administration REST API Controller"""

from typing import List
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from marshmallow import Schema, fields, ValidationError
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger

from ai_server.services.user_admin_svc import UserAdminService
from ai_server.dao.database import db, User, Bot
from ai_server.decorators.role_required import role_required
from ai_server.dto.user_dto import UserDto
from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE

CONTROLLER_NAME = "users"
CONTROLLER_PATH = "/users"

bp = Blueprint(CONTROLLER_NAME, __name__)


class UserRegistrationSchema(Schema):
    """Schema for user registration validation"""

    name = fields.String(required=True, validate=lambda x: len(x.strip()) > 0)
    email = fields.Email(required=True)
    password = fields.String(required=True)
    assigned_bot_ids = fields.List(fields.Int(), allow_none=True)


class UserUpdateSchema(Schema):
    """Schema for user update validation"""

    name = fields.String(
        required=False, validate=lambda x: len(x.strip()) > 0 if x else True
    )
    email = fields.Email(required=False)
    # assigned_bot_ids=fields.List(fields.Int(), allow_none=True)


class RoleChangeSchema(Schema):
    """Schema for role change validation"""

    role = fields.String(
        required=True, validate=lambda x: x in [ADMIN_ROLE, USER_ROLE, GUEST_ROLE]
    )


class PasswordChangeSchema(Schema):
    """Schema for password change validation"""

    old_password = fields.String(required=True)
    new_password = fields.String(required=True, validate=lambda x: len(x) >= 6)


class ReassignChildrenSchema(Schema):
    """Schema for children reassignment validation"""

    old_parent_id = fields.Integer(required=True)
    new_parent_id = fields.Integer(required=True)


class PatchBotSchema(Schema):
    """Schema for selected bot validation"""

    selected_bot_id = fields.Integer(required=False, allow_none=True)
    assigned_bot_ids = fields.List(
        fields.Int(),
        allow_none=True,
        required=False,
    )


# Services initialization
app_logger = BotFactoryLogger()
logger = BotFactoryLogger()
user_admin_svc = UserAdminService()
user_registration_schema = UserRegistrationSchema()
user_update_schema = UserUpdateSchema()
role_change_schema = RoleChangeSchema()
password_change_schema = PasswordChangeSchema()
reassign_children_schema = ReassignChildrenSchema()
patch_bot_schema = PatchBotSchema()


@bp.route(f"{CONTROLLER_PATH}", methods=["POST"])
def register():
    """Register a new user"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = user_registration_schema.load(data)

        existing_user = User.query.filter_by(mail=validated_data["email"]).first()
        if existing_user:
            return jsonify({"error": "Email already registered"}), HTTPStatus.CONFLICT

        user = user_admin_svc.register_new_user(
            validated_data["email"], validated_data["name"], validated_data["password"]
        )

        app_logger.info(f"New user registered: {validated_data['email']}")
        return jsonify(
            {"message": "User registered successfully", "user": user}
        ), HTTPStatus.CREATED

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"User registration error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/self", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
def update_users_self():
    """Update current user's information"""
    user_id = get_jwt_identity()
    return _update_users(user_id)


@bp.route(f"{CONTROLLER_PATH}/guest/<int:guest_id>", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
def update_users_guest(guest_id):
    """Update guest user's information"""
    try:
        user_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()

        if not guest:
            return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND

        if guest.parent_id != int(user_id):
            return jsonify(
                {"error": f"Unable to update user {guest_id} - not your guest"}
            ), HTTPStatus.FORBIDDEN

        return _update_users(guest_id)

    except Exception as exc:
        logger.error(f"Guest user update error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>", methods=["PUT"])
@role_required([ADMIN_ROLE])
def update_users_admin(user_id):
    """Update user's information (admin only)"""
    return _update_users(user_id)


def _update_users(user_id):
    """Internal function to update user information"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = user_update_schema.load(data)

        user_dto = user_admin_svc.update(user_id, validated_data)

        return jsonify(
            {"message": "User updated successfully", "user": user_dto.to_dict()}
        ), HTTPStatus.OK

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"User update error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/guest", methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE])
def register_guest():
    """Register a new guest user"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = user_registration_schema.load(data)
        parent_id = get_jwt_identity()

        existing_user = User.query.filter_by(mail=validated_data["email"]).first()
        if existing_user:
            return jsonify({"error": "Email already registered"}), HTTPStatus.CONFLICT

        user_admin_svc.register_new_guest(parent_id, validated_data)

        app_logger.info(
            f"New guest user registered by parent {parent_id}: {validated_data['email']}"
        )
        return jsonify(
            {"message": "Guest user registered successfully"}
        ), HTTPStatus.CREATED

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"Guest registration error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_all_users():
    """Get all users (admin only)"""
    try:
        users = user_admin_svc.get_all_users()
        return jsonify({"users": users}), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Get all users error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/guests", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_all_guests():
    """Get all guest users for current user"""
    try:
        user_id = get_jwt_identity()
        users: List[UserDto] = user_admin_svc.get_children_users(user_id)
        return jsonify([user_dto.to_dict() for user_dto in users]), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Get guest users error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/role/<role>", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_users_by_role(role):
    """Get users by role"""
    try:
        if role not in [ADMIN_ROLE, USER_ROLE, GUEST_ROLE]:
            return jsonify({"error": "Invalid role"}), HTTPStatus.BAD_REQUEST

        users = user_admin_svc.get_users_by_role(role)
        return jsonify({"users": users}), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Get users by role error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/children/self", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_children_self():
    """Get children users for current user"""
    user_id = get_jwt_identity()
    return _get_children(user_id)


@bp.route(f"{CONTROLLER_PATH}/children/<int:parent_id>", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_children_admin(parent_id):
    """Get children users for a parent (admin only)"""
    return _get_children(parent_id)


def _get_children(parent_id):
    """Internal function to get children users for a parent"""
    try:
        users: List[UserDto] = user_admin_svc.get_children_users(parent_id)
        return jsonify({"children": [user.to_dict() for user in users]}), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Get children users error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/self", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
def delete_user_self():
    user_id = get_jwt_identity()
    return delete_user(user_id)


@bp.route(f"{CONTROLLER_PATH}/guest/<int:guest_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
def delete_user_guest(guest_id):
    try:
        user_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()
        if guest.parent_id == int(user_id):
            return delete_user(guest_id)
        return jsonify(
            msg=f"Unable to delete  user {guest_id} because it's not your guest."
        ), 200
    except Exception as exc:
        msg = f"Exception while activating user: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE])
def delete_user_admin(user_id):
    delete_user(user_id)


def delete_user(user_id):
    """Supprime un utilisateur"""
    try:
        user_admin_svc.delete_user(user_id)
        # security_logger.info(f'User {user_id} deleted by admin {get_jwt_identity()}')
        return jsonify(msg="User deleted successfully"), 200
    except Exception as exc:
        msg = f"Exception while deleting user: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>/role", methods=["PUT"])
@role_required([ADMIN_ROLE])
def change_role(user_id):
    """Change le rôle d'un utilisateur"""
    try:
        data = request.get_json()
        new_role = data.get("role")
        if not new_role:
            raise ApiError("Role is required", 400)

        user = user_admin_svc.change_user_role(user_id, new_role)
        app_logger.info(
            f"Role changed for user {user_id} by admin {get_jwt_identity()}"
        )
        return jsonify(
            msg="Role updated successfully",
            user={
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "roles": user.roles,
            },
        ), 200
    except Exception as exc:
        msg = f"Exception while changing user role: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/password/self", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
def change_password_self():
    """Change le mot de passe de l'utilisateur connecté"""
    try:
        user_id = get_jwt_identity()
        return change_password(user_id)
    except ApiError as exc:
        msg = f"Exception while changing password: {exc}"
        code = exc.status_code
        raise ApiError(msg, code)

    except Exception as exc:
        msg = f"Exception while changing password: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/password/guest/<int:guest_id>", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
def change_password_guest(guest_id):
    """Change le mot de passe de l'utilisateur connecté"""
    try:
        guest = User.query.filter_by(id=guest_id).first()
        user_id = get_jwt_identity()
        if guest.parent_id == int(user_id):
            return change_password(guest_id)
        return ApiError(
            f"Unable to change the  password because user {guest_id} it's not your guest.",
            200,
        )
    except ApiError as exc:
        msg = f"Exception while changing guest password: {exc}"
        code = exc.status_code
        raise ApiError(msg, code)
    except Exception as exc:
        msg = f"Exception while changing guest password: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


def change_password(user_id):
    """Change le mot de passe de l'utilisateur connecté"""

    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        raise ApiError("Old and new passwords are required", 400)
    if new_password == old_password:
        raise ApiError("Password update failed. New password equal old password", 400)

    user_admin_svc.change_password(user_id, old_password, new_password)
    # security_logger.info(f'Password changed for user {user_id}')
    return jsonify(msg="Password updated successfully"), 200


@bp.route(f"{CONTROLLER_PATH}/<int:guest_id>/deactivate/guest", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
def deactivate_user_guest(guest_id):
    try:
        user_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()

        if guest.parent_id == int(user_id):
            return deactivate_user(guest_id)
        return jsonify(
            msg=f"Unable to deactivate user {guest_id} because it's not your guest."
        ), 200
    except Exception as exc:
        msg = f"Exception while deactivating user: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>/deactivate", methods=["PUT"])
@role_required([ADMIN_ROLE])
def deactivate_user_admin(user_id):
    return deactivate_user(user_id)


def deactivate_user(user_id):
    """Désactive un compte utilisateur"""
    try:
        user_dto: UserDto = user_admin_svc.deactivate_user(user_id)
        # security_logger.info(f'User {user_id} deactivated by admin {get_jwt_identity()}')
        return jsonify(
            msg="User deactivated successfully", user=user_dto.to_dict()
        ), 200
    except Exception as exc:
        msg = f"Exception while deactivating user: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/<int:guest_id>/activate/guest", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
def activate_user_guest(guest_id):
    try:
        user_id = get_jwt_identity()
        children = User.query.filter_by(id=guest_id).first()
        if children.parent_id == int(user_id):
            return activate_user(guest_id)
        return jsonify(
            msg=f"Unable to activate user {guest_id} because it's not your guest."
        ), 200
    except Exception as exc:
        msg = f"Exception while activating guest: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)
        msg = f"Exception while activating user: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>/activate", methods=["PUT"])
@role_required([ADMIN_ROLE])
def activate_user_admin(user_id):
    return activate_user(user_id)


def activate_user(user_id):
    """Active un compte utilisateur"""
    try:
        user_dto: UserDto = user_admin_svc.activate_user(user_id)
        # security_logger.info(f'User {user_id} activated by admin {get_jwt_identity()}')
        return jsonify(msg="User activated successfully", user=user_dto.to_dict()), 200
    except Exception as exc:
        msg = f"Exception while activating user: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/reassign-children", methods=["PUT"])
@role_required([ADMIN_ROLE])
def reassign_children():
    """Réassigne les utilisateurs enfants à un nouveau parent"""
    try:
        data = request.get_json()
        old_parent_id = data.get("old_parent_id")
        new_parent_id = data.get("new_parent_id")

        if not old_parent_id or not new_parent_id:
            raise ApiError("Old and new parent IDs are required", 400)

        user_admin_svc.reassign_children(old_parent_id, new_parent_id)
        app_logger.info(
            f"Children reassigned from {old_parent_id} to {new_parent_id} by admin {get_jwt_identity()}"
        )
        return jsonify(msg="Children reassigned successfully"), 200
    except Exception as exc:
        msg = f"Exception while reassigning children: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/self", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
def get_user_self():
    user_id = get_jwt_identity()
    return get_user(user_id)


@bp.route(f"{CONTROLLER_PATH}/guest/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_user_guest(guest_id):
    try:
        user_id = get_jwt_identity()
        children = User.query.filter_by(id=guest_id).first()
        if children.parent_id == user_id:
            return get_user(user_id)
        return jsonify(
            msg=f"Unable to get user {guest_id} because it's not your guest."
        ), 200
    except Exception as exc:
        msg = f"Exception while activating user: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_user_admin(user_id):
    return get_user(user_id)


def get_user(user_id):
    """Récupère les détails d'un utilisateur"""
    try:
        user_dto = user_admin_svc.get_user_dto_by_id(user_id)
        if not user_dto:
            raise ApiError("User not found", 404)
        logger.info(f"user_dto {user_dto}")
        logger.info(f"user_dto.to_dict() {user_dto.to_dict()}")
        return jsonify(user_dto.to_dict()), 200

    except Exception as exc:
        msg = f"Exception while getting user details: {exc}"
        logger.error(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/self", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
def patch_user_self():
    """Update current user's selected bot"""
    user_id = get_jwt_identity()
    return _patch_user(user_id)


@bp.route(f"{CONTROLLER_PATH}/guest/<int:guest_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE])
def patch_user_guest(guest_id):
    # """Update guest user's selected bot"""
    try:
        parent_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()

        if not guest:
            return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND

        if guest.parent_id != int(parent_id):
            return jsonify(
                {"error": f"Unable to update user {guest_id} - not your guest"}
            ), HTTPStatus.FORBIDDEN

        return _patch_user(parent_id, guest_id)

    except Exception as exc:
        logger.error(f"Guest user patch error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE])
def patch_user_admin(guest_id):
    """Update user's selected bot (admin only)"""
    parent_id = get_jwt_identity()
    return _patch_user(parent_id, guest_id)


def _patch_user(parent_id, guest_id=-1):
    """Internal function to update user's selected bot"""
    try:
        if not request.is_json:
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = patch_bot_schema.load(data)

        user_dto = user_admin_svc.patch_user(parent_id, guest_id, validated_data)
        logger.debug(f"User {guest_id} patched successfully by parent {parent_id}")

        return jsonify(user_dto.to_dict()), HTTPStatus.OK

    except ValidationError as e:
        return jsonify({"error": e.messages}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.error(f"User patch error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/selected_bot/self", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
def get_selected_bot_self():
    """Get current user's selected bot"""
    user_id = get_jwt_identity()
    return _get_selected_bot(user_id)


@bp.route(f"{CONTROLLER_PATH}/selected_bot/guest/<int:guest_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
def get_selected_bot_guest(guest_id):
    """Get guest user's selected bot"""
    try:
        user_id = get_jwt_identity()
        guest = User.query.filter_by(id=guest_id).first()

        if not guest:
            return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND

        if guest.parent_id != int(user_id):
            return jsonify(
                {"error": f"Unable to access user {guest_id} - not your guest"}
            ), HTTPStatus.FORBIDDEN

        return _get_selected_bot(guest_id)

    except Exception as exc:
        logger.error(f"Guest selected bot retrieval error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/selected_bot/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE])
def get_selected_bot_admin(user_id):
    """Get user's selected bot (admin only)"""
    return _get_selected_bot(user_id)


def _get_selected_bot(user_id):
    """Internal function to get user's selected bot"""
    try:
        user: User = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), HTTPStatus.NOT_FOUND

        if not user.selected_bot_id:
            return jsonify({"selected_bot_id": None, "bot": None}), HTTPStatus.OK

        bot: Bot = Bot.query.get(user.selected_bot_id)
        if not bot:
            return jsonify(
                {"selected_bot_id": user.selected_bot_id, "bot": None}
            ), HTTPStatus.OK

        return jsonify(
            {
                "selected_bot_id": user.selected_bot_id,
            }
        ), HTTPStatus.OK
    except Exception as exc:
        logger.error(f"Error retrieving selected bot: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
