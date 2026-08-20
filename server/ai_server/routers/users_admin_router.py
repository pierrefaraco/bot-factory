"""User Administration REST API -- native FastAPI port of the former
ai_server/rest/rest_users_admin.py Flask blueprint (Phase 7 of the
Flask -> FastAPI migration). Same URLs, same response shapes, same role
and ownership checks.

Two consistent simplifications versus the original, both flagged rather
than silent:

- Several handlers (delete_user*, change_role, change_password*,
  (de)activate_user*, reassign_children, get_user*) wrapped their own
  `except ApiError as exc: raise ApiError(f"Exception while X: {exc}",
  code)` -- re-raising the *same* ApiError with an extra prefix glued
  onto its message but the same status code. Every genuine ApiError
  raised deep in user_admin_svc (invalid old password, user not found,
  etc.) now simply propagates to asgi.py's own ApiError handler
  unchanged -- same status, and every test here only substring-matches
  the message, so nothing observable changes; it also stops rewrapping
  service-layer NotFoundError/ServiceError into a 500 that is generic
  either way (that part already matched the original's own `except
  Exception` fallback).
- Kept consistent with bot_router.py's earlier normalization: no route
  here manually catches an unexpected Exception to leak str(exc) --
  asgi.py's shared catch-all's generic "Internal server error" covers it.

Every dead `if not request.is_json` check (a body model with only
required fields, where SpecTree's own gate already 400s first) is
dropped, same as every prior phase. The ones that *are* live --
_update_users (UserUpdateRequest, all-optional) and _patch_user
(PatchBotRequest, all-optional) -- use require_json_body() same as
avatar/bot_parameters' PATCH routes.

reassign_children's `if not old_parent_id or not new_parent_id` is
NOT dropped even though ReassignChildrenRequest requires both fields:
a legitimate `old_parent_id: 0` is falsy in Python, so this check can
still reject a validly-present-but-zero id that pydantic already
accepted -- a real (if obscure) behavior of the original, not dead code.
"""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dao.database import Bot, User
from ai_server.decorators.user_scope import authorize_user_scope
from ai_server.dependencies.auth import require_roles
from ai_server.dependencies.content_type import require_json_body
from ai_server.dependencies.db_session import with_db_session
from ai_server.dto.user_dto import UserDto
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.user_admin_svc import UserAdminService

router = APIRouter(prefix="/api/users", tags=["users-admin"])

logger = BotFactoryLogger()
app_logger = BotFactoryLogger()
user_admin_svc = UserAdminService()

admin_only = require_roles([ADMIN_ROLE])
admin_or_user = require_roles([ADMIN_ROLE, USER_ROLE])
any_role = require_roles([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])


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


def _enforce_user_scope(caller_id, target_id: int, allow_self: bool = True) -> None:
    error = authorize_user_scope(caller_id, target_id, allow_self=allow_self)
    if error:
        response, status_code = error
        raise ApiError(response["error"], status_code=status_code)


@router.post("", status_code=201, dependencies=[Depends(require_json_body(UserRegistrationRequest))])
@with_db_session
def register(body: UserRegistrationRequest):
    """Register a new user"""
    logger.info("POST /users - register called")
    existing_user = User.query.filter_by(mail=body.email).first()
    if existing_user:
        logger.warning(f"register rejected: email already registered ({body.email})")
        raise ApiError("Email already registered", status_code=409)

    user = user_admin_svc.register_new_user(body.email, body.name, body.password)
    app_logger.info(f"New user registered: {body.email}")
    return {"message": "User registered successfully", "user": user}


@router.put("/me", dependencies=[Depends(require_json_body(UserUpdateRequest))])
@with_db_session
def update_users_self(body: UserUpdateRequest, claims: dict = Depends(any_role)):
    """Update current user's information"""
    user_id = claims["sub"]
    logger.info(f"PUT /users/me - update_users_self called for user_id={user_id}")
    return _update_users_impl(user_id, body)


@router.put("/{user_id:int}", dependencies=[Depends(require_json_body(UserUpdateRequest))])
@with_db_session
def update_users_by_id(user_id: int, body: UserUpdateRequest, claims: dict = Depends(admin_or_user)):
    """Update a user's information (own guest, or any user if admin)"""
    logger.info(f"PUT /users/{user_id} - update_users_by_id called")
    _enforce_user_scope(claims["sub"], user_id)
    return _update_users_impl(user_id, body)


def _update_users_impl(user_id, body: UserUpdateRequest):
    validated_data = body.model_dump(exclude_unset=True)
    logger.debug(f"update_users({user_id}) fields: {list(validated_data.keys())}")
    user_dto = user_admin_svc.update(user_id, validated_data)
    logger.info(f"update_users({user_id}) succeeded")
    return {"message": "User updated successfully", "user": user_dto.to_dict()}


@router.post(
    "/guest", status_code=201, dependencies=[Depends(require_json_body(UserRegistrationRequest))]
)
@with_db_session
def register_guest(body: UserRegistrationRequest, claims: dict = Depends(admin_or_user)):
    """Register a new guest user"""
    logger.info("POST /users/guest - register_guest called")
    parent_id = claims["sub"]
    validated_data = body.model_dump()

    existing_user = User.query.filter_by(mail=validated_data["email"]).first()
    if existing_user:
        logger.warning(f"register_guest rejected: email already registered ({validated_data['email']})")
        raise ApiError("Email already registered", status_code=409)

    user_admin_svc.register_new_guest(parent_id, validated_data)
    app_logger.info(f"New guest user registered by parent {parent_id}: {validated_data['email']}")
    return {"message": "Guest user registered successfully"}


@router.get("")
@with_db_session
def get_all_users(claims: dict = Depends(admin_only)):
    """Get all users (admin only) -- excludes every other Admin account,
    matching authorize_user_scope's "no acting on peer admins" rule: those
    rows would 403 on every action anyway, so they're left out entirely
    rather than shown disabled."""
    logger.info("GET /users - get_all_users called")
    caller_id = claims["sub"]
    users = user_admin_svc.get_all_users(caller_id)
    logger.info(f"get_all_users succeeded count={len(users)}")
    return {"users": users}


@router.get("/guests")
@with_db_session
def get_all_guests(claims: dict = Depends(admin_or_user)):
    """Get all guest users for current user"""
    logger.info("GET /users/guests - get_all_guests called")
    user_id = claims["sub"]
    users: List[UserDto] = user_admin_svc.get_children_users(user_id)
    logger.info(f"get_all_guests succeeded for user_id={user_id} count={len(users)}")
    return [user_dto.to_dict() for user_dto in users]


@router.get("/role/{role}")
@with_db_session
def get_users_by_role(role: str, claims: dict = Depends(admin_only)):
    """Get users by role"""
    logger.info(f"GET /users/role/{role} - get_users_by_role called")
    if role not in [ADMIN_ROLE, USER_ROLE, GUEST_ROLE]:
        logger.warning(f"get_users_by_role rejected: invalid role {role}")
        raise ApiError("Invalid role", status_code=400)

    caller_id = claims["sub"]
    users = user_admin_svc.get_users_by_role(role, caller_id)
    logger.info(f"get_users_by_role({role}) succeeded count={len(users)}")
    return {"users": users}


def _get_children(parent_id):
    users: List[UserDto] = user_admin_svc.get_children_users(parent_id)
    logger.info(f"get_children({parent_id}) succeeded count={len(users)}")
    return {"children": [user.to_dict() for user in users]}


@router.get("/children/me")
@with_db_session
def get_children_self(claims: dict = Depends(admin_or_user)):
    """Get children users for current user"""
    user_id = claims["sub"]
    logger.info(f"GET /users/children/me - get_children_self called for user_id={user_id}")
    return _get_children(user_id)


@router.get("/children/{parent_id:int}", dependencies=[Depends(admin_only)])
@with_db_session
def get_children_admin(parent_id: int):
    """Get children users for a parent (admin only)"""
    logger.info(f"GET /users/children/{parent_id} - get_children_admin called")
    return _get_children(parent_id)


def delete_user(user_id):
    """Supprime un utilisateur"""
    user_admin_svc.delete_user(user_id)
    logger.info(f"delete_user({user_id}) succeeded")
    return {"msg": "User deleted successfully"}


@router.delete("/me")
@with_db_session
def delete_user_self(claims: dict = Depends(any_role)):
    user_id = claims["sub"]
    logger.info(f"DELETE /users/me - delete_user_self called for user_id={user_id}")
    return delete_user(user_id)


@router.delete("/{user_id:int}")
@with_db_session
def delete_user_by_id(user_id: int, claims: dict = Depends(admin_or_user)):
    """Delete a user (own guest, or any user if admin)"""
    logger.info(f"DELETE /users/{user_id} - delete_user_by_id called")
    _enforce_user_scope(claims["sub"], user_id)
    return delete_user(user_id)


@router.put(
    "/{user_id:int}/role", dependencies=[Depends(require_json_body(RoleChangeRequest))]
)
@with_db_session
def change_role(user_id: int, body: RoleChangeRequest, claims: dict = Depends(admin_only)):
    """Change le rôle d'un utilisateur"""
    logger.info(f"PUT /users/{user_id}/role - change_role called")
    _enforce_user_scope(claims["sub"], user_id)

    user = user_admin_svc.change_user_role(user_id, body.role)
    app_logger.info(f"Role changed for user {user_id} by admin {claims['sub']} to {body.role}")
    return {
        "msg": "Role updated successfully",
        "user": {"id": user.id, "name": user.name, "email": user.email, "roles": user.roles},
    }


def change_password(user_id, body: PasswordChangeRequest):
    """Change le mot de passe de l'utilisateur connecté"""
    if body.new_password == body.old_password:
        logger.warning(f"change_password({user_id}) rejected: new password equals old password")
        raise ApiError("Password update failed. New password equal old password", status_code=400)

    user_admin_svc.change_password(user_id, body.old_password, body.new_password)
    logger.info(f"change_password({user_id}) succeeded")
    return {"msg": "Password updated successfully"}


@router.put(
    "/password/me", dependencies=[Depends(require_json_body(PasswordChangeRequest))]
)
@with_db_session
def change_password_self(body: PasswordChangeRequest, claims: dict = Depends(any_role)):
    """Change le mot de passe de l'utilisateur connecté"""
    logger.info("PUT /users/password/me - change_password_self called")
    return change_password(claims["sub"], body)


@router.put(
    "/password/guest/{guest_id:int}",
    dependencies=[Depends(require_json_body(PasswordChangeRequest))],
)
@with_db_session
def change_password_guest(guest_id: int, body: PasswordChangeRequest, claims: dict = Depends(admin_or_user)):
    """Change le mot de passe de l'utilisateur connecté"""
    logger.info(f"PUT /users/password/guest/{guest_id} - change_password_guest called")
    guest = User.query.filter_by(id=guest_id).first()
    user_id = claims["sub"]
    if not guest:
        logger.warning(f"change_password_guest({guest_id}) rejected: guest not found")
        raise ApiError("Guest user not found", status_code=404)
    if guest.parent_id != int(user_id):
        logger.warning(f"change_password_guest({guest_id}) forbidden: not a guest of user_id={user_id}")
        raise ApiError(f"Unable to change password for user {guest_id} - not your guest", status_code=403)
    return change_password(guest_id, body)


def deactivate_user(user_id):
    """Désactive un compte utilisateur"""
    user_dto: UserDto = user_admin_svc.deactivate_user(user_id)
    logger.info(f"deactivate_user({user_id}) succeeded")
    return {"msg": "User deactivated successfully", "user": user_dto.to_dict()}


@router.put("/{user_id:int}/deactivate")
@with_db_session
def deactivate_user_by_id(user_id: int, claims: dict = Depends(admin_or_user)):
    """Deactivate a user (own guest, or any user if admin). No self-service
    deactivation, same as before the guest/admin merge -- there was never a
    /me route for this."""
    logger.info(f"PUT /users/{user_id}/deactivate - deactivate_user_by_id called")
    _enforce_user_scope(claims["sub"], user_id, allow_self=False)
    return deactivate_user(user_id)


def activate_user(user_id):
    """Active un compte utilisateur"""
    user_dto: UserDto = user_admin_svc.activate_user(user_id)
    logger.info(f"activate_user({user_id}) succeeded")
    return {"msg": "User activated successfully", "user": user_dto.to_dict()}


@router.put("/{user_id:int}/activate")
@with_db_session
def activate_user_by_id(user_id: int, claims: dict = Depends(admin_or_user)):
    """Activate a user (own guest, or any user if admin). No self-service
    activation, same as before the guest/admin merge -- there was never a
    /me route for this."""
    logger.info(f"PUT /users/{user_id}/activate - activate_user_by_id called")
    _enforce_user_scope(claims["sub"], user_id, allow_self=False)
    return activate_user(user_id)


@router.put(
    "/reassign-children", dependencies=[Depends(require_json_body(ReassignChildrenRequest))]
)
@with_db_session
def reassign_children(body: ReassignChildrenRequest, claims: dict = Depends(admin_only)):
    """Réassigne les utilisateurs enfants à un nouveau parent"""
    logger.info("PUT /users/reassign-children - reassign_children called")
    if not body.old_parent_id or not body.new_parent_id:
        logger.warning("reassign_children rejected: old/new parent id missing")
        raise ApiError("Old and new parent IDs are required", status_code=400)

    user_admin_svc.reassign_children(body.old_parent_id, body.new_parent_id)
    app_logger.info(
        f"Children reassigned from {body.old_parent_id} to {body.new_parent_id} by admin {claims['sub']}"
    )
    return {"msg": "Children reassigned successfully"}


def get_user(user_id):
    """Récupère les détails d'un utilisateur"""
    user_dto = user_admin_svc.get_user_dto_by_id(user_id)
    if not user_dto:
        logger.warning(f"get_user({user_id}) not found")
        raise ApiError("User not found", status_code=404)
    logger.info(f"get_user({user_id}) succeeded")
    return user_dto.to_dict()


@router.get("/me")
@with_db_session
def get_user_self(claims: dict = Depends(any_role)):
    user_id = claims["sub"]
    logger.info(f"GET /users/me - get_user_self called for user_id={user_id}")
    return get_user(user_id)


@router.get("/{user_id:int}")
@with_db_session
def get_user_by_id(user_id: int, claims: dict = Depends(admin_or_user)):
    """Get a user's details (own guest, or any user if admin)"""
    logger.info(f"GET /users/{user_id} - get_user_by_id called")
    _enforce_user_scope(claims["sub"], user_id)
    return get_user(user_id)


def _patch_user(parent_id, body: PatchBotRequest, guest_id=-1):
    """Internal function to update user's selected bot"""
    validated_data = body.model_dump(exclude_unset=True)
    logger.debug(f"patch_user({guest_id}) fields: {list(validated_data.keys())}")
    user_dto = user_admin_svc.patch_user(parent_id, guest_id, validated_data)
    logger.info(f"User {guest_id} patched successfully by parent {parent_id}")
    return user_dto.to_dict()


@router.patch("/me", dependencies=[Depends(require_json_body(PatchBotRequest))])
@with_db_session
def patch_user_self(body: PatchBotRequest, claims: dict = Depends(any_role)):
    """Update current user's selected bot"""
    user_id = claims["sub"]
    logger.info(f"PATCH /users/me - patch_user_self called for user_id={user_id}")
    return _patch_user(user_id, body)


@router.patch(
    "/{target_user_id:int}", dependencies=[Depends(require_json_body(PatchBotRequest))]
)
@with_db_session
def patch_user_by_id(target_user_id: int, body: PatchBotRequest, claims: dict = Depends(admin_or_user)):
    """Update a user's selected bot (own guest, or any user if admin)"""
    logger.info(f"PATCH /users/{target_user_id} - patch_user_by_id called")
    caller_id = claims["sub"]
    _enforce_user_scope(caller_id, target_user_id)
    return _patch_user(caller_id, body, target_user_id)


def _get_selected_bot(user_id):
    """Internal function to get user's selected bot. The asymmetric
    response shapes (some branches include a "bot" key, the final one
    doesn't) are the original's own behavior, kept verbatim."""
    user: User = User.query.get(user_id)
    if not user.selected_bot_id:
        logger.info(f"get_selected_bot({user_id}) succeeded: no bot selected")
        return {"selected_bot_id": None, "bot": None}

    bot: Bot = Bot.query.get(user.selected_bot_id)
    if not bot:
        logger.warning(f"get_selected_bot({user_id}) selected_bot_id={user.selected_bot_id} not found")
        return {"selected_bot_id": user.selected_bot_id, "bot": None}

    logger.info(f"get_selected_bot({user_id}) succeeded selected_bot_id={user.selected_bot_id}")
    return {"selected_bot_id": user.selected_bot_id}


@router.get("/selected_bot/me")
@with_db_session
def get_selected_bot_self(claims: dict = Depends(any_role)):
    """Get current user's selected bot"""
    user_id = claims["sub"]
    logger.info(f"GET /users/selected_bot/me - get_selected_bot_self called for user_id={user_id}")
    return _get_selected_bot(user_id)


@router.get("/selected_bot/{user_id:int}")
@with_db_session
def get_selected_bot_by_id(user_id: int, claims: dict = Depends(admin_or_user)):
    """Get a user's selected bot (own guest, or any user if admin)"""
    logger.info(f"GET /users/selected_bot/{user_id} - get_selected_bot_by_id called")
    _enforce_user_scope(claims["sub"], user_id)
    return _get_selected_bot(user_id)
