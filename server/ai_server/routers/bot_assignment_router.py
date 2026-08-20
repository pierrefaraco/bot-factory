"""Bot Guest Assignment REST API -- native FastAPI port of the former
ai_server/rest/rest_bot_assignment.py Flask blueprint (Phase 5 of the
Flask -> FastAPI migration). Same URLs, same response shapes, same role
and ownership checks; unhandled exceptions fall through to asgi.py's
catch-all 500 handler.

Every body model in this blueprint (BotGuestAssignmentRequest,
BotGuestAssignmentUpdateRequest, BotGuestAssignmentRefRequest) has only
required fields, so a wrong Content-Type always falls into the "Field
required" branch of require_json_body() -- the original's explicit
`if not request.is_json` checks were dead code, and so were
remove_assignment/check_assignment's manual `if "bot_id" not in data`
presence checks (SpecTree's own required-field gate already rejects a
body missing either field before the handler runs). This port skips
reproducing that unreachable code and reads straight off the validated
body model instead.
"""

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dao.database import User
from ai_server.dependencies.auth import require_roles
from ai_server.dependencies.content_type import require_json_body
from ai_server.dependencies.db_session import with_db_session
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.bot_assignment_svc import BotAssignmentService

router = APIRouter(prefix="/api/bot-guest-assignment", tags=["bot-assignment"])

logger = BotFactoryLogger()
bot_assignment_svc = BotAssignmentService()

admin_or_user = require_roles([ADMIN_ROLE, USER_ROLE])
any_role = require_roles([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])


class BotGuestAssignmentRequest(BaseModel):
    """Schema for bot guest assignment validation"""

    bot_id: int
    guest_user_id: int
    is_active: bool = True


class BotGuestAssignmentUpdateRequest(BaseModel):
    """Schema for updating bot guest assignment"""

    is_active: bool


class BotGuestAssignmentRefRequest(BaseModel):
    """Schema referencing an assignment by bot and guest user"""

    bot_id: int
    guest_user_id: int


def _current_user(user_id) -> User:
    user: User = User.query.filter_by(id=user_id).first()
    if not user:
        raise ApiError("User not found", status_code=401)
    return user


@router.post(
    "", status_code=201, dependencies=[Depends(require_json_body(BotGuestAssignmentRequest))]
)
@with_db_session
def create_assignment(body: BotGuestAssignmentRequest, claims: dict = Depends(admin_or_user)):
    """Create a new bot guest assignment"""
    logger.info("POST /bot-guest-assignment - create_assignment called")
    user_id = claims["sub"]
    logger.debug(
        f"create_assignment payload: bot_id={body.bot_id} "
        f"guest_user_id={body.guest_user_id} is_active={body.is_active}"
    )
    _current_user(user_id)

    # Add the assigner information; the service expects "user_id" for the
    # assignee (the DTO field is named guest_user_id for API clarity).
    validated_data = body.model_dump()
    validated_data["assigned_by"] = user_id
    validated_data["user_id"] = validated_data["guest_user_id"]

    assignment_dto = bot_assignment_svc.create(validated_data)
    if not assignment_dto:
        logger.warning(f"create_assignment failed for assigned_by={user_id}")
        raise ApiError("Failed to create assignment", status_code=500)

    logger.info(f"create_assignment succeeded id={assignment_dto.id} assigned_by={user_id}")
    return assignment_dto.to_dict()


@router.get("/parent/{parent_user_id:int}", dependencies=[Depends(admin_or_user)])
@with_db_session
def get_assignments_by_parent(parent_user_id: int, claims: dict = Depends(admin_or_user)):
    """Get all assignments created by a parent user"""
    logger.info(f"GET /bot-guest-assignment/parent/{parent_user_id} - get_assignments_by_parent called")
    user_id = claims["sub"]
    user = _current_user(user_id)

    if user.roles != ADMIN_ROLE and int(user_id) != parent_user_id:
        logger.warning(f"get_assignments_by_parent({parent_user_id}) forbidden for user_id={user_id}")
        raise ApiError("Forbidden", status_code=403)

    assignments = bot_assignment_svc.get_assignments_by_parent(parent_user_id)
    logger.info(f"get_assignments_by_parent({parent_user_id}) succeeded count={len(assignments)}")
    return [assignment.to_dict() for assignment in assignments]


def _authorize_guest_scope(user: User, user_id, guest_user_id: int) -> None:
    """Shared by get_assignments_by_guest and get_assigned_bot_ids: a
    Guest may only look at their own assignments; a User/Admin may look
    at a guest's assignments only if that guest is their own (Admin is
    unrestricted)."""
    if user.roles == GUEST_ROLE:
        if int(user_id) != guest_user_id:
            raise ApiError("Forbidden", status_code=403)
    elif user.roles in [USER_ROLE, ADMIN_ROLE]:
        guest_user: User = User.query.filter_by(id=guest_user_id).first()
        if not guest_user or (user.roles != ADMIN_ROLE and guest_user.parent_id != int(user_id)):
            raise ApiError("Forbidden", status_code=403)


@router.get("/guest/{guest_user_id:int}", dependencies=[Depends(any_role)])
@with_db_session
def get_assignments_by_guest(guest_user_id: int, claims: dict = Depends(any_role)):
    """Get all assignments for a guest user"""
    logger.info(f"GET /bot-guest-assignment/guest/{guest_user_id} - get_assignments_by_guest called")
    user_id = claims["sub"]
    user = _current_user(user_id)
    try:
        _authorize_guest_scope(user, user_id, guest_user_id)
    except ApiError:
        logger.warning(f"get_assignments_by_guest({guest_user_id}) forbidden for user_id={user_id}")
        raise

    assignments = bot_assignment_svc.get_assignments_by_user(guest_user_id)
    logger.info(f"get_assignments_by_guest({guest_user_id}) succeeded count={len(assignments)}")
    return [assignment.to_dict() for assignment in assignments]


@router.get("/guest/{guest_user_id:int}/bot-ids", dependencies=[Depends(any_role)])
@with_db_session
def get_assigned_bot_ids(guest_user_id: int, claims: dict = Depends(any_role)):
    """Get list of bot IDs assigned to a guest user"""
    logger.info(f"GET /bot-guest-assignment/guest/{guest_user_id}/bot-ids - get_assigned_bot_ids called")
    user_id = claims["sub"]
    user = _current_user(user_id)
    try:
        _authorize_guest_scope(user, user_id, guest_user_id)
    except ApiError:
        logger.warning(f"get_assigned_bot_ids({guest_user_id}) forbidden for user_id={user_id}")
        raise

    bot_ids = bot_assignment_svc.get_assigned_bot_ids_for_user(guest_user_id)
    logger.info(f"get_assigned_bot_ids({guest_user_id}) succeeded count={len(bot_ids)}")
    return {"bot_ids": bot_ids}


@router.put(
    "/{assignment_id:int}",
    dependencies=[Depends(require_json_body(BotGuestAssignmentUpdateRequest))],
)
@with_db_session
def update_assignment(
    assignment_id: int, body: BotGuestAssignmentUpdateRequest, claims: dict = Depends(admin_or_user)
):
    """Update a bot guest assignment"""
    logger.info(f"PUT /bot-guest-assignment/{assignment_id} - update_assignment called")
    user_id = claims["sub"]
    user = _current_user(user_id)

    assignment = bot_assignment_svc.get_dto_by_id(assignment_id)
    if not assignment:
        logger.warning(f"update_assignment({assignment_id}) not found")
        raise ApiError("Assignment not found", status_code=404)
    if user.roles != ADMIN_ROLE and assignment.assigned_by != int(user_id):
        logger.warning(f"update_assignment({assignment_id}) forbidden for user_id={user_id}")
        raise ApiError("Forbidden", status_code=403)

    updated_assignment = bot_assignment_svc.update(assignment_id, body.model_dump())
    logger.info(f"update_assignment({assignment_id}) succeeded")
    return updated_assignment.to_dict()


@router.delete("/{assignment_id:int}", status_code=204, dependencies=[Depends(admin_or_user)])
@with_db_session
def delete_assignment(assignment_id: int, claims: dict = Depends(admin_or_user)):
    """Delete a bot guest assignment"""
    logger.info(f"DELETE /bot-guest-assignment/{assignment_id} - delete_assignment called")
    user_id = claims["sub"]
    user = _current_user(user_id)

    assignment = bot_assignment_svc.get_dto_by_id(assignment_id)
    if not assignment:
        logger.warning(f"delete_assignment({assignment_id}) not found")
        raise ApiError("Assignment not found", status_code=404)
    if user.roles != ADMIN_ROLE and assignment.assigned_by != int(user_id):
        logger.warning(f"delete_assignment({assignment_id}) forbidden for user_id={user_id}")
        raise ApiError("Forbidden", status_code=403)

    if not bot_assignment_svc.delete(assignment_id):
        logger.warning(f"delete_assignment({assignment_id}) not found on delete")
        raise ApiError("Assignment not found", status_code=404)

    logger.info(f"delete_assignment({assignment_id}) succeeded")
    return Response(status_code=204)


@router.delete(
    "/remove", dependencies=[Depends(require_json_body(BotGuestAssignmentRefRequest))]
)
@with_db_session
def remove_assignment(body: BotGuestAssignmentRefRequest, claims: dict = Depends(admin_or_user)):
    """Remove assignment between a bot and guest user"""
    logger.info("DELETE /bot-guest-assignment/remove - remove_assignment called")
    _current_user(claims["sub"])

    logger.debug(f"remove_assignment payload: bot_id={body.bot_id} guest_user_id={body.guest_user_id}")
    if not bot_assignment_svc.remove_assignment(body.bot_id, body.guest_user_id):
        logger.warning(f"remove_assignment not found for bot_id={body.bot_id} guest_user_id={body.guest_user_id}")
        raise ApiError("Assignment not found", status_code=404)

    logger.info(f"remove_assignment succeeded for bot_id={body.bot_id} guest_user_id={body.guest_user_id}")
    return {"message": "Assignment removed successfully"}


@router.post(
    "/check", dependencies=[Depends(require_json_body(BotGuestAssignmentRefRequest))]
)
@with_db_session
def check_assignment(body: BotGuestAssignmentRefRequest, claims: dict = Depends(any_role)):
    """Check if a bot is assigned to a guest user"""
    logger.info("POST /bot-guest-assignment/check - check_assignment called")
    logger.debug(f"check_assignment payload: bot_id={body.bot_id} guest_user_id={body.guest_user_id}")
    is_assigned = bot_assignment_svc.is_bot_assigned_to_user(body.bot_id, body.guest_user_id)
    logger.info(f"check_assignment succeeded is_assigned={is_assigned}")
    return {"is_assigned": is_assigned}
