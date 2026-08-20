"""Avatar Management REST API -- native FastAPI port of the former
ai_server/rest/rest_avatar.py Flask blueprint (Phase 2 of the
Flask -> FastAPI migration). Same URLs, same response shapes, same role
checks; unhandled exceptions fall through to asgi.py's catch-all 500
handler.

Content-Type contract: this blueprint had no @bp.before_request guard, so
a wrong Content-Type only ever showed up via SpecTree's automatic
@api.validate(json=...) treating the body as absent -- see
dependencies/content_type.py's require_json_body() docstring for exactly
how that plays out differently for the required-bot_id models here vs.
the all-optional AvatarPatchRequest.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Response

from ai_server.config.constant import ADMIN_ROLE, GUEST_ROLE, USER_ROLE
from ai_server.dependencies.auth import require_roles
from ai_server.dependencies.content_type import require_json_body
from ai_server.dependencies.db_session import with_db_session
from ai_server.exceptions.api_error import ApiError
from ai_server.log.bot_factory_logger import BotFactoryLogger
from ai_server.services.avatar_svc import AvatarService
from pydantic import BaseModel

router = APIRouter(prefix="/api/avatar", tags=["avatar"])

logger = BotFactoryLogger()
avatar_service = AvatarService()

admin_or_user = require_roles([ADMIN_ROLE, USER_ROLE])
any_role = require_roles([ADMIN_ROLE, USER_ROLE, GUEST_ROLE])


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


@router.post(
    "/random",
    status_code=201,
    dependencies=[Depends(admin_or_user), Depends(require_json_body(AvatarRandomRequest))],
)
@with_db_session
def create_random_avatar(body: AvatarRandomRequest):
    """Create a random avatar for a bot"""
    logger.info("POST /avatar/random - create_random_avatar called")
    avatar_dto = avatar_service.create_random_avatar(body.bot_id)
    logger.info(f"create_random_avatar succeeded for bot_id={body.bot_id} avatar_id={avatar_dto.id}")
    return avatar_dto.to_dict()


@router.patch(
    "",
    status_code=204,
    dependencies=[Depends(admin_or_user), Depends(require_json_body(AvatarPatchRequest))],
)
@with_db_session
def patch_avatar(body: AvatarPatchRequest):
    """Partially update an avatar"""
    logger.info("PATCH /avatar - patch_avatar called")
    avatar_service.patch_avatar(body.model_dump(exclude_unset=True))
    logger.info(f"patch_avatar succeeded for bot_id={body.bot_id}")
    return Response(status_code=204)


@router.post(
    "",
    status_code=201,
    dependencies=[Depends(admin_or_user), Depends(require_json_body(AvatarRequest))],
)
@with_db_session
def create_avatar(body: AvatarRequest):
    """Create an avatar"""
    logger.info("POST /avatar - create_avatar called")
    avatar_dto = avatar_service.create(body.model_dump(exclude_unset=True))
    logger.info(f"create_avatar succeeded for bot_id={body.bot_id} avatar_id={avatar_dto.id}")
    return avatar_dto.to_dict()


@router.put(
    "",
    dependencies=[Depends(admin_or_user), Depends(require_json_body(AvatarRequest))],
)
@with_db_session
def update_avatar(body: AvatarRequest):
    """Update an avatar"""
    logger.info("PUT /avatar - update_avatar called")
    avatar_dto = avatar_service.update_and_return_datat(body.model_dump(exclude_unset=True))
    logger.info(f"update_avatar succeeded for bot_id={body.bot_id} avatar_id={avatar_dto.id}")
    return avatar_dto.to_dict()


@router.get("/{bot_id}", dependencies=[Depends(any_role)])
@with_db_session
def get_avatar_by_bot_id(bot_id: int):
    """Get avatar by bot ID"""
    logger.info(f"GET /avatar/{bot_id} - get_avatar_by_bot_id called")
    avatar_dto = avatar_service.get_avatar_by_bot_id(bot_id)
    if not avatar_dto:
        logger.warning(f"get_avatar_by_bot_id({bot_id}) not found")
        raise ApiError("Avatar not found", status_code=404)
    logger.info(f"get_avatar_by_bot_id({bot_id}) succeeded")
    return avatar_dto.to_dict()


@router.delete("/{bot_id}", status_code=204, dependencies=[Depends(admin_or_user)])
@with_db_session
def delete_avatar(bot_id: int):
    """Delete avatar by bot ID"""
    logger.info(f"DELETE /avatar/{bot_id} - delete_avatar called")
    if not avatar_service.delete_avatar_by_bot_id(bot_id):
        logger.warning(f"delete_avatar({bot_id}) not found")
        raise ApiError("Avatar not found", status_code=404)
    logger.info(f"delete_avatar({bot_id}) succeeded")
    return Response(status_code=204)
