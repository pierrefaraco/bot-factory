"""User Administration REST API Controller"""

from typing import List
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from http import HTTPStatus
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, ValidationError

from ai_server.config.openapi import api, pydantic_error_messages
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger

from ai_server.services.user_admin_svc import UserAdminService
from ai_server.dao.database import db, User, Bot
from ai_server.decorators.role_required import role_required
from ai_server.decorators.user_scope import authorize_user_scope
from ai_server.dto.user_dto import UserDto
from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE

CONTROLLER_NAME = "users"
CONTROLLER_PATH = "/users"

bp = Blueprint(CONTROLLER_NAME, __name__)


class UserRegistrationRequest(BaseModel):
    """Schema for user registration validation"""

    name: str = Field(min_length=1)
    email: EmailStr
    password: str
    assigned_bot_ids: Optional[list[int]] = None


class UserUpdateRequest(BaseModel):
    """Schema for user update validation"""

    name: Optional[str] = Field(default=None, min_length=1)
    email: Optional[EmailStr] = None


class RoleChangeRequest(BaseModel):
    """Schema for role change validation"""

    # ADMIN deliberately excluded: there is no API path to create a second
    # Admin account at all (the only one is the pre-seeded super-admin from
    # SUPER_ADMIN_LOGIN/PASSWORD) -- authorize_user_scope's "no admin acts
    # on another admin" rule stays in place as defense-in-depth regardless.
    role: Literal[USER_ROLE, GUEST_ROLE]


class PasswordChangeRequest(BaseModel):
    """Schema for password change validation"""

    old_password: str
    new_password: str = Field(min_length=6)


class ReassignChildrenRequest(BaseModel):
    """Schema for children reassignment validation"""

    old_parent_id: int
    new_parent_id: int


class PatchBotRequest(BaseModel):
    """Schema for selected bot validation"""

    selected_bot_id: Optional[int] = None
    assigned_bot_ids: Optional[list[int]] = None


# Services initialization
app_logger = BotFactoryLogger()
logger = BotFactoryLogger()
user_admin_svc = UserAdminService()


@bp.route(f"{CONTROLLER_PATH}", methods=["POST"])
@api.validate(json=UserRegistrationRequest, tags=["users-admin"])
def register():
    """Register a new user"""
    logger.info(f"POST {CONTROLLER_PATH} - register called")
    try:
        if not request.is_json:
            logger.warning("register rejected: Content-Type is not application/json")
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = UserRegistrationRequest.model_validate(data).model_dump()

        existing_user = User.query.filter_by(mail=validated_data["email"]).first()
        if existing_user:
            logger.warning(f"register rejected: email already registered ({validated_data['email']})")
            return jsonify({"error": "Email already registered"}), HTTPStatus.CONFLICT

        user = user_admin_svc.register_new_user(
            validated_data["email"], validated_data["name"], validated_data["password"]
        )

        app_logger.info(
            f"New user registered: {validated_data['email']} - status={HTTPStatus.CREATED}"
        )
        return jsonify(
            {"message": "User registered successfully", "user": user}
        ), HTTPStatus.CREATED

    except ValidationError as e:
        logger.warning(f"register validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"User registration error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/me", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(json=UserUpdateRequest, tags=["users-admin"], security={"BearerAuth": []})
def update_users_self():
    """Update current user's information"""
    user_id = get_jwt_identity()
    logger.info(f"PUT {CONTROLLER_PATH}/me - update_users_self called for user_id={user_id}")
    return _update_users(user_id)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=UserUpdateRequest, tags=["users-admin"], security={"BearerAuth": []})
def update_users_by_id(user_id):
    """Update a user's information (own guest, or any user if admin)"""
    logger.info(f"PUT {CONTROLLER_PATH}/{user_id} - update_users_by_id called")
    try:
        error = authorize_user_scope(user_id)
        if error:
            logger.warning(f"update_users_by_id({user_id}) rejected by authorize_user_scope")
            return error
        return _update_users(user_id)
    except Exception as exc:
        logger.exception(f"User update error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


def _update_users(user_id):
    """Internal function to update user information"""
    try:
        if not request.is_json:
            logger.warning(f"update_users({user_id}) rejected: Content-Type is not application/json")
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = UserUpdateRequest.model_validate(data).model_dump(exclude_unset=True)
        logger.debug(f"update_users({user_id}) fields: {list(validated_data.keys())}")

        user_dto = user_admin_svc.update(user_id, validated_data)

        logger.info(f"update_users({user_id}) succeeded - status={HTTPStatus.OK}")
        return jsonify(
            {"message": "User updated successfully", "user": user_dto.to_dict()}
        ), HTTPStatus.OK

    except ValidationError as e:
        logger.warning(f"update_users({user_id}) validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"User update error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/guest", methods=["POST"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=UserRegistrationRequest, tags=["users-admin"], security={"BearerAuth": []})
def register_guest():
    """Register a new guest user"""
    logger.info(f"POST {CONTROLLER_PATH}/guest - register_guest called")
    try:
        if not request.is_json:
            logger.warning("register_guest rejected: Content-Type is not application/json")
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = UserRegistrationRequest.model_validate(data).model_dump()
        parent_id = get_jwt_identity()

        existing_user = User.query.filter_by(mail=validated_data["email"]).first()
        if existing_user:
            logger.warning(f"register_guest rejected: email already registered ({validated_data['email']})")
            return jsonify({"error": "Email already registered"}), HTTPStatus.CONFLICT

        user_admin_svc.register_new_guest(parent_id, validated_data)

        app_logger.info(
            f"New guest user registered by parent {parent_id}: {validated_data['email']} "
            f"- status={HTTPStatus.CREATED}"
        )
        return jsonify(
            {"message": "Guest user registered successfully"}
        ), HTTPStatus.CREATED

    except ValidationError as e:
        logger.warning(f"register_guest validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"Guest registration error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}", methods=["GET"])
@role_required([ADMIN_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def get_all_users():
    """Get all users (admin only) -- excludes every other Admin account,
    matching authorize_user_scope's "no acting on peer admins" rule: those
    rows would 403 on every action anyway, so they're left out entirely
    rather than shown disabled."""
    logger.info(f"GET {CONTROLLER_PATH} - get_all_users called")
    try:
        caller_id = get_jwt_identity()
        users = user_admin_svc.get_all_users(caller_id)
        logger.info(f"get_all_users succeeded count={len(users)} - status={HTTPStatus.OK}")
        return jsonify({"users": users}), HTTPStatus.OK
    except Exception as exc:
        logger.exception(f"Get all users error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/guests", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def get_all_guests():
    """Get all guest users for current user"""
    logger.info(f"GET {CONTROLLER_PATH}/guests - get_all_guests called")
    try:
        user_id = get_jwt_identity()
        users: List[UserDto] = user_admin_svc.get_children_users(user_id)
        logger.info(f"get_all_guests succeeded for user_id={user_id} count={len(users)} - status={HTTPStatus.OK}")
        return jsonify([user_dto.to_dict() for user_dto in users]), HTTPStatus.OK
    except Exception as exc:
        logger.exception(f"Get guest users error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/role/<role>", methods=["GET"])
@role_required([ADMIN_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def get_users_by_role(role):
    """Get users by role"""
    logger.info(f"GET {CONTROLLER_PATH}/role/{role} - get_users_by_role called")
    try:
        if role not in [ADMIN_ROLE, USER_ROLE, GUEST_ROLE]:
            logger.warning(f"get_users_by_role rejected: invalid role {role}")
            return jsonify({"error": "Invalid role"}), HTTPStatus.BAD_REQUEST

        caller_id = get_jwt_identity()
        users = user_admin_svc.get_users_by_role(role, caller_id)
        logger.info(f"get_users_by_role({role}) succeeded count={len(users)} - status={HTTPStatus.OK}")
        return jsonify({"users": users}), HTTPStatus.OK
    except Exception as exc:
        logger.exception(f"Get users by role error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/children/me", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def get_children_self():
    """Get children users for current user"""
    user_id = get_jwt_identity()
    logger.info(f"GET {CONTROLLER_PATH}/children/me - get_children_self called for user_id={user_id}")
    return _get_children(user_id)


@bp.route(f"{CONTROLLER_PATH}/children/<int:parent_id>", methods=["GET"])
@role_required([ADMIN_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def get_children_admin(parent_id):
    """Get children users for a parent (admin only)"""
    logger.info(f"GET {CONTROLLER_PATH}/children/{parent_id} - get_children_admin called")
    return _get_children(parent_id)


def _get_children(parent_id):
    """Internal function to get children users for a parent"""
    try:
        users: List[UserDto] = user_admin_svc.get_children_users(parent_id)
        logger.info(
            f"get_children({parent_id}) succeeded count={len(users)} - status={HTTPStatus.OK}"
        )
        return jsonify({"children": [user.to_dict() for user in users]}), HTTPStatus.OK
    except Exception as exc:
        logger.exception(f"Get children users error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/me", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def delete_user_self():
    user_id = get_jwt_identity()
    logger.info(f"DELETE {CONTROLLER_PATH}/me - delete_user_self called for user_id={user_id}")
    return delete_user(user_id)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>", methods=["DELETE"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def delete_user_by_id(user_id):
    """Delete a user (own guest, or any user if admin)"""
    logger.info(f"DELETE {CONTROLLER_PATH}/{user_id} - delete_user_by_id called")
    try:
        error = authorize_user_scope(user_id)
        if error:
            logger.warning(f"delete_user_by_id({user_id}) rejected by authorize_user_scope")
            return error
        return delete_user(user_id)
    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while deleting user: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


def delete_user(user_id):
    """Supprime un utilisateur"""
    try:
        user_admin_svc.delete_user(user_id)
        logger.info(
            f"delete_user({user_id}) succeeded, deleted by admin {get_jwt_identity()} "
            f"- status=200"
        )
        return jsonify(msg="User deleted successfully"), 200
    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while deleting user: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>/role", methods=["PUT"])
@role_required([ADMIN_ROLE])
@api.validate(json=RoleChangeRequest, tags=["users-admin"], security={"BearerAuth": []})
def change_role(user_id):
    """Change le rôle d'un utilisateur"""
    logger.info(f"PUT {CONTROLLER_PATH}/{user_id}/role - change_role called")
    try:
        error = authorize_user_scope(user_id)
        if error:
            logger.warning(f"change_role({user_id}) rejected by authorize_user_scope")
            return error

        data = request.get_json()
        new_role = data.get("role")
        if not new_role:
            logger.warning(f"change_role({user_id}) rejected: role is required")
            raise ApiError("Role is required", 400)

        logger.debug(f"change_role({user_id}) requested new_role={new_role}")
        user = user_admin_svc.change_user_role(user_id, new_role)
        app_logger.info(
            f"Role changed for user {user_id} by admin {get_jwt_identity()} "
            f"to {new_role} - status=200"
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
    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while changing user role: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/password/me", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(json=PasswordChangeRequest, tags=["users-admin"], security={"BearerAuth": []})
def change_password_self():
    """Change le mot de passe de l'utilisateur connecté"""
    logger.info(f"PUT {CONTROLLER_PATH}/password/me - change_password_self called")
    try:
        user_id = get_jwt_identity()
        return change_password(user_id)
    except ApiError as exc:
        msg = f"Exception while changing password: {exc}"
        code = exc.status_code
        raise ApiError(msg, code)

    except Exception as exc:
        msg = f"Exception while changing password: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/password/guest/<int:guest_id>", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=PasswordChangeRequest, tags=["users-admin"], security={"BearerAuth": []})
def change_password_guest(guest_id):
    """Change le mot de passe de l'utilisateur connecté"""
    logger.info(f"PUT {CONTROLLER_PATH}/password/guest/{guest_id} - change_password_guest called")
    try:
        guest = User.query.filter_by(id=guest_id).first()
        user_id = get_jwt_identity()
        if not guest:
            logger.warning(f"change_password_guest({guest_id}) rejected: guest not found")
            return jsonify({"error": "Guest user not found"}), HTTPStatus.NOT_FOUND
        if guest.parent_id != int(user_id):
            logger.warning(
                f"change_password_guest({guest_id}) forbidden: not a guest of user_id={user_id}"
            )
            return jsonify(
                {"error": f"Unable to change password for user {guest_id} - not your guest"}
            ), HTTPStatus.FORBIDDEN
        return change_password(guest_id)
    except ApiError as exc:
        msg = f"Exception while changing guest password: {exc}"
        code = exc.status_code
        raise ApiError(msg, code)
    except Exception as exc:
        msg = f"Exception while changing guest password: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


def change_password(user_id):
    """Change le mot de passe de l'utilisateur connecté"""

    # Never log request payload here: it carries old_password/new_password.
    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        logger.warning(f"change_password({user_id}) rejected: old/new password missing")
        raise ApiError("Old and new passwords are required", 400)
    if new_password == old_password:
        logger.warning(f"change_password({user_id}) rejected: new password equals old password")
        raise ApiError("Password update failed. New password equal old password", 400)

    user_admin_svc.change_password(user_id, old_password, new_password)
    logger.info(f"change_password({user_id}) succeeded - status=200")
    return jsonify(msg="Password updated successfully"), 200


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>/deactivate", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def deactivate_user_by_id(user_id):
    """Deactivate a user (own guest, or any user if admin). No self-service
    deactivation, same as before the guest/admin merge -- there was never a
    /me route for this."""
    logger.info(f"PUT {CONTROLLER_PATH}/{user_id}/deactivate - deactivate_user_by_id called")
    try:
        error = authorize_user_scope(user_id, allow_self=False)
        if error:
            logger.warning(f"deactivate_user_by_id({user_id}) rejected by authorize_user_scope")
            return error
        return deactivate_user(user_id)
    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while deactivating user: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


def deactivate_user(user_id):
    """Désactive un compte utilisateur"""
    try:
        user_dto: UserDto = user_admin_svc.deactivate_user(user_id)
        logger.info(
            f"deactivate_user({user_id}) succeeded, deactivated by admin {get_jwt_identity()} "
            f"- status=200"
        )
        return jsonify(
            msg="User deactivated successfully", user=user_dto.to_dict()
        ), 200
    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while deactivating user: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>/activate", methods=["PUT"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def activate_user_by_id(user_id):
    """Activate a user (own guest, or any user if admin). No self-service
    activation, same as before the guest/admin merge -- there was never a
    /me route for this."""
    logger.info(f"PUT {CONTROLLER_PATH}/{user_id}/activate - activate_user_by_id called")
    try:
        error = authorize_user_scope(user_id, allow_self=False)
        if error:
            logger.warning(f"activate_user_by_id({user_id}) rejected by authorize_user_scope")
            return error
        return activate_user(user_id)
    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while activating user: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


def activate_user(user_id):
    """Active un compte utilisateur"""
    try:
        user_dto: UserDto = user_admin_svc.activate_user(user_id)
        logger.info(
            f"activate_user({user_id}) succeeded, activated by admin {get_jwt_identity()} "
            f"- status=200"
        )
        return jsonify(msg="User activated successfully", user=user_dto.to_dict()), 200
    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while activating user: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/reassign-children", methods=["PUT"])
@role_required([ADMIN_ROLE])
@api.validate(json=ReassignChildrenRequest, tags=["users-admin"], security={"BearerAuth": []})
def reassign_children():
    """Réassigne les utilisateurs enfants à un nouveau parent"""
    logger.info(f"PUT {CONTROLLER_PATH}/reassign-children - reassign_children called")
    try:
        data = request.get_json()
        old_parent_id = data.get("old_parent_id")
        new_parent_id = data.get("new_parent_id")

        if not old_parent_id or not new_parent_id:
            logger.warning("reassign_children rejected: old/new parent id missing")
            raise ApiError("Old and new parent IDs are required", 400)

        user_admin_svc.reassign_children(old_parent_id, new_parent_id)
        app_logger.info(
            f"Children reassigned from {old_parent_id} to {new_parent_id} "
            f"by admin {get_jwt_identity()} - status=200"
        )
        return jsonify(msg="Children reassigned successfully"), 200
    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while reassigning children: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/me", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def get_user_self():
    user_id = get_jwt_identity()
    logger.info(f"GET {CONTROLLER_PATH}/me - get_user_self called for user_id={user_id}")
    return get_user(user_id)


@bp.route(f"{CONTROLLER_PATH}/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def get_user_by_id(user_id):
    """Get a user's details (own guest, or any user if admin)"""
    logger.info(f"GET {CONTROLLER_PATH}/{user_id} - get_user_by_id called")
    try:
        error = authorize_user_scope(user_id)
        if error:
            logger.warning(f"get_user_by_id({user_id}) rejected by authorize_user_scope")
            return error
        return get_user(user_id)
    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while retrieving user: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


def get_user(user_id):
    """Récupère les détails d'un utilisateur"""
    try:
        user_dto = user_admin_svc.get_user_dto_by_id(user_id)
        if not user_dto:
            logger.warning(f"get_user({user_id}) not found")
            raise ApiError("User not found", 404)
        logger.debug(f"get_user({user_id}) resolved user_dto")
        logger.info(f"get_user({user_id}) succeeded - status=200")
        return jsonify(user_dto.to_dict()), 200

    except ApiError:
        raise
    except Exception as exc:
        msg = f"Exception while getting user details: {exc}"
        logger.exception(msg)
        raise ApiError(msg, 500)


@bp.route(f"{CONTROLLER_PATH}/me", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(json=PatchBotRequest, tags=["users-admin"], security={"BearerAuth": []})
def patch_user_self():
    """Update current user's selected bot"""
    user_id = get_jwt_identity()
    logger.info(f"PATCH {CONTROLLER_PATH}/me - patch_user_self called for user_id={user_id}")
    return _patch_user(user_id)


@bp.route(f"{CONTROLLER_PATH}/<int:target_user_id>", methods=["PATCH"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(json=PatchBotRequest, tags=["users-admin"], security={"BearerAuth": []})
def patch_user_by_id(target_user_id):
    """Update a user's selected bot (own guest, or any user if admin)"""
    logger.info(f"PATCH {CONTROLLER_PATH}/{target_user_id} - patch_user_by_id called")
    try:
        error = authorize_user_scope(target_user_id)
        if error:
            logger.warning(f"patch_user_by_id({target_user_id}) rejected by authorize_user_scope")
            return error
        return _patch_user(get_jwt_identity(), target_user_id)
    except Exception as exc:
        logger.exception(f"User patch error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


def _patch_user(parent_id, guest_id=-1):
    """Internal function to update user's selected bot"""
    try:
        if not request.is_json:
            logger.warning(f"patch_user({guest_id}) rejected: Content-Type is not application/json")
            return jsonify(
                {"error": "Content-Type must be application/json"}
            ), HTTPStatus.BAD_REQUEST

        data = request.get_json()
        validated_data = PatchBotRequest.model_validate(data).model_dump(exclude_unset=True)
        logger.debug(f"patch_user({guest_id}) fields: {list(validated_data.keys())}")

        user_dto = user_admin_svc.patch_user(parent_id, guest_id, validated_data)
        logger.info(
            f"User {guest_id} patched successfully by parent {parent_id} "
            f"- status={HTTPStatus.OK}"
        )

        return jsonify(user_dto.to_dict()), HTTPStatus.OK

    except ValidationError as e:
        logger.warning(f"patch_user({guest_id}) validation error: {pydantic_error_messages(e)}")
        return jsonify({"error": pydantic_error_messages(e)}), HTTPStatus.BAD_REQUEST
    except Exception as exc:
        logger.exception(f"User patch error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


@bp.route(f"{CONTROLLER_PATH}/selected_bot/me", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def get_selected_bot_self():
    """Get current user's selected bot"""
    user_id = get_jwt_identity()
    logger.info(f"GET {CONTROLLER_PATH}/selected_bot/me - get_selected_bot_self called for user_id={user_id}")
    return _get_selected_bot(user_id)


@bp.route(f"{CONTROLLER_PATH}/selected_bot/<int:user_id>", methods=["GET"])
@role_required([ADMIN_ROLE, USER_ROLE])
@api.validate(tags=["users-admin"], security={"BearerAuth": []})
def get_selected_bot_by_id(user_id):
    """Get a user's selected bot (own guest, or any user if admin)"""
    logger.info(f"GET {CONTROLLER_PATH}/selected_bot/{user_id} - get_selected_bot_by_id called")
    try:
        error = authorize_user_scope(user_id)
        if error:
            logger.warning(f"get_selected_bot_by_id({user_id}) rejected by authorize_user_scope")
            return error
        return _get_selected_bot(user_id)
    except Exception as exc:
        logger.exception(f"Selected bot retrieval error: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


def _get_selected_bot(user_id):
    """Internal function to get user's selected bot"""
    try:
        user: User = User.query.get(user_id)
        if not user:
            logger.warning(f"get_selected_bot({user_id}) rejected: user not found")
            return jsonify({"error": "User not found"}), HTTPStatus.NOT_FOUND

        if not user.selected_bot_id:
            logger.info(f"get_selected_bot({user_id}) succeeded: no bot selected - status={HTTPStatus.OK}")
            return jsonify({"selected_bot_id": None, "bot": None}), HTTPStatus.OK

        bot: Bot = Bot.query.get(user.selected_bot_id)
        if not bot:
            logger.warning(
                f"get_selected_bot({user_id}) selected_bot_id={user.selected_bot_id} not found"
            )
            return jsonify(
                {"selected_bot_id": user.selected_bot_id, "bot": None}
            ), HTTPStatus.OK

        logger.info(
            f"get_selected_bot({user_id}) succeeded selected_bot_id={user.selected_bot_id} "
            f"- status={HTTPStatus.OK}"
        )
        return jsonify(
            {
                "selected_bot_id": user.selected_bot_id,
            }
        ), HTTPStatus.OK
    except Exception as exc:
        logger.exception(f"Error retrieving selected bot: {exc}")
        return jsonify(
            {"error": "Internal server error"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
